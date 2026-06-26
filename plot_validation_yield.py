"""PN yield plots across scenarios.

Two rows of "yield" diagnostics:

  Row 1  Notification yield  (effort -> STI+ partners found)
    (a)  STI+ partners per 1000 notifications, F-index (VDS-triggered)
    (b)  STI+ partners per 1000 notifications, M-index (UDS-triggered)
    (c)  STI+ partners per PN trigger (F-index vs M-index, grouped bars)

  Row 2  Treatment efficiency / detection volume
    (d)  Treatment efficiency by disease (% successful), grouped per scenario
    (e)  Cumulative unnecessary treatments by disease (millions), grouped
    (f)  Cumulative STI+ partners found (millions), per scenario

"STI+ partners" = attending - attended_no_sti (any of NG/CT/TV/syph current
infection at attendance). "Treatment efficiency" = successful /
(successful + unnecessary) per disease.

Reads results/scenarios_smoke.kavg.csv. Writes
figures/fig_validation_yield.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent
KAVG = REPO / 'results' / 'scenarios_smoke.kavg.csv'
FIG_DIR = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

CELL_ORDER = [
    ('SOC', 'SOC', '#444444'),
    ('POC_c-baseline_p-baseline_b-none', 'POC', '#1f77b4'),
    ('POC_c-high_p-baseline_b-none', 'POC+CS', '#2ca02c'),
    ('POC_c-baseline_p-high_b-none', 'POC+PN', '#d62728'),
    ('POC_c-baseline_p-baseline_b-high', 'POC+BP', '#9467bd'),
]
DISEASES = ['ng', 'ct', 'tv', 'syph']
DNAME = {'ng': 'NG', 'ct': 'CT', 'tv': 'TV', 'syph': 'Syph'}
DCOLOR = {'ng': '#1f77b4', 'ct': '#ff7f0e', 'tv': '#2ca02c', 'syph': '#d62728'}


def set_font(size=9):
    if Path(FONT).exists():
        sc.fonts(add=FONT)
        sc.options(font='Libertinus Sans', fontsize=size)
    else:
        sc.options(fontsize=size)


def _med(kavg, col):
    out = []
    for cell, _, _ in CELL_ORDER:
        v = kavg.loc[kavg.cell == cell, col] if col in kavg.columns else pd.Series([0.0])
        out.append(float(v.median()) if len(v) else 0.0)
    return np.array(out)


def _bar(ax, values, ylabel=None, title=None, ymax_pad=1.15, fmt='{:.0f}'):
    x = np.arange(len(CELL_ORDER))
    colors = [c for _, _, c in CELL_ORDER]
    ax.bar(x, values, color=colors, alpha=0.9)
    for i, v in enumerate(values):
        if np.isfinite(v) and v > 0:
            ax.text(i, v * 1.02, fmt.format(v), ha='center', va='bottom',
                    fontsize=7, color='#333')
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab, _ in CELL_ORDER], fontsize=7.5,
                       rotation=20, ha='right')
    vmax = np.nanmax(values) if len(values) else 0
    if vmax > 0:
        ax.set_ylim(bottom=0, top=vmax * ymax_pad)
    ax.tick_params(axis='y', labelsize=7.5)
    ax.spines[['top', 'right']].set_visible(False)
    if title:
        ax.set_title(title, fontsize=10, pad=4)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)


def _grouped_bar(ax, group_values, group_labels, group_colors,
                 ylabel=None, title=None, ymax_pad=1.20, fmt='{:.0f}'):
    """group_values: list of arrays, one per group, each of length n_scenarios."""
    n_groups = len(group_values)
    n_scen = len(CELL_ORDER)
    x = np.arange(n_scen)
    width = 0.8 / n_groups
    for k, (vals, lab, col) in enumerate(zip(group_values, group_labels, group_colors)):
        offsets = x + (k - (n_groups - 1) / 2) * width
        ax.bar(offsets, vals, width=width, color=col, alpha=0.9, label=lab)
        for xi, v in zip(offsets, vals):
            if np.isfinite(v) and v > 0:
                ax.text(xi, v * 1.02, fmt.format(v), ha='center', va='bottom',
                        fontsize=6, color='#333')
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab, _ in CELL_ORDER], fontsize=7.5,
                       rotation=20, ha='right')
    vmax = max(np.nanmax(v) if len(v) else 0 for v in group_values)
    if vmax > 0:
        ax.set_ylim(bottom=0, top=vmax * ymax_pad)
    ax.tick_params(axis='y', labelsize=7.5)
    ax.spines[['top', 'right']].set_visible(False)
    if title:
        ax.set_title(title, fontsize=10, pad=4)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)
    ax.legend(fontsize=7, frameon=False, loc='upper left')


def main():
    set_font(9)
    kavg = pd.read_csv(KAVG)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Row 1: notification yield ----
    # Yield per 1000 notifications, by index sex.
    # STI+ partners = attending - attended_no_sti (partner-side, any STI).
    # Notifications and attendances are the OPPOSITE-sex of the index, so:
    #   F-index pathway -> M-partner notifications/attendance
    #   M-index pathway -> F-partner notifications/attendance.
    notif_m = _med(kavg, 'pn_new_notified_m')
    notif_f = _med(kavg, 'pn_new_notified_f')
    att_m = _med(kavg, 'pn_new_attending_m')
    att_f = _med(kavg, 'pn_new_attending_f')
    att_no_sti_m = _med(kavg, 'pn_new_attended_no_sti_m')
    att_no_sti_f = _med(kavg, 'pn_new_attended_no_sti_f')

    # STI+ partners attending.
    stipos_m = att_m - att_no_sti_m
    stipos_f = att_f - att_no_sti_f

    yield_per_1000_F_idx = np.where(notif_m > 0, stipos_m / notif_m * 1000, 0.0)
    yield_per_1000_M_idx = np.where(notif_f > 0, stipos_f / notif_f * 1000, 0.0)

    # Per-index yield (STI+ partners found per PN trigger).
    idx_total_f = _med(kavg, 'pn_new_index_total_f')
    idx_total_m = _med(kavg, 'pn_new_index_total_m')
    yield_per_idx_F = np.where(idx_total_f > 0, stipos_m / idx_total_f, 0.0)
    yield_per_idx_M = np.where(idx_total_m > 0, stipos_f / idx_total_m, 0.0)

    fig, axes = pl.subplots(2, 3, figsize=(13.5, 8.5))

    _bar(axes[0, 0], yield_per_1000_F_idx,
         ylabel='STI+ partners per 1000 notifications',
         title='(a) F-index pathway (VDS): notification yield',
         fmt='{:.0f}')
    _bar(axes[0, 1], yield_per_1000_M_idx,
         ylabel='STI+ partners per 1000 notifications',
         title='(b) M-index pathway (UDS): notification yield',
         fmt='{:.0f}')

    _grouped_bar(axes[0, 2],
                 [yield_per_idx_F, yield_per_idx_M],
                 ['F-index (VDS)', 'M-index (UDS)'],
                 ['#3b86c4', '#e6772d'],
                 ylabel='STI+ partners found per PN trigger',
                 title='(c) STI+ partners per index PN trigger',
                 fmt='{:.2f}')

    # ---- Row 2: treatment efficiency / volume ----
    # Treatment efficiency: successful / (successful + unnecessary) per disease.
    succ = {d: _med(kavg, f'{d}_new_treated_success') for d in DISEASES}
    unn = {d: _med(kavg, f'{d}_new_treated_unnecessary') for d in DISEASES}
    eff = {}
    for d in DISEASES:
        total = succ[d] + unn[d]
        eff[d] = np.where(total > 0, succ[d] / total * 100, np.nan)

    _grouped_bar(axes[1, 0],
                 [eff[d] for d in DISEASES],
                 [DNAME[d] for d in DISEASES],
                 [DCOLOR[d] for d in DISEASES],
                 ylabel='% treatments that hit a real STI',
                 title='(d) Treatment efficiency by disease',
                 fmt='{:.0f}%', ymax_pad=1.15)
    axes[1, 0].set_ylim(0, 105)

    # Unnecessary treatments by disease (millions), grouped per scenario.
    _grouped_bar(axes[1, 1],
                 [unn[d] / 1e6 for d in DISEASES],
                 [DNAME[d] for d in DISEASES],
                 [DCOLOR[d] for d in DISEASES],
                 ylabel='unnecessary tx 2027-40 (millions)',
                 title='(e) Cumulative unnecessary treatments',
                 fmt='{:.1f}')

    # Cumulative STI+ partners found (millions): F-index + M-index split.
    _grouped_bar(axes[1, 2],
                 [stipos_m / 1e6, stipos_f / 1e6],
                 ['F-index -> M+ partners', 'M-index -> F+ partners'],
                 ['#3b86c4', '#e6772d'],
                 ylabel='STI+ partners found 2027-40\n(millions)',
                 title='(f) Cumulative STI+ partners detected via PN',
                 fmt='{:.2f}')

    fig.text(0.5, 0.012,
             'Validation: 5 cells x 5 draws (exp 06 top 5) x K=5 seeds; per-cell '
             'median across draws. "STI+ partners" = partners attending minus '
             'partners with no NG/CT/TV/syph at attendance. Treatment efficiency '
             'computed from cumulative 2027-40 successful and unnecessary tx counts.',
             ha='center', fontsize=6.6, color='#666')
    fig.subplots_adjust(left=0.065, right=0.99, top=0.95, bottom=0.075,
                        wspace=0.32, hspace=0.42)
    out = FIG_DIR / 'fig_validation_yield.png'
    fig.savefig(out, dpi=200)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
