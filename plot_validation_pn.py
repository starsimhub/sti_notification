"""PN warranted vs over cascade across scenarios, split by index sex.

Two rows: female-index pathway (VDS) and male-index pathway (UDS). Each
shows the cascade triggered by that index sex: indexes -> notifications
to opposite-sex partners -> opposite-sex attendances. Each bar is
stacked by warrant status.

Reads results/scenarios_smoke.kavg.csv. Writes
figures/fig_validation_pn_cascade.png.

Warranted = index had an STI when PN fired.
Over     = index had no STI (BV-only or false-positive syndromic
treatment). The user's hypothesis: under SOC syndromic, the female
(VDS) pathway should be heavily over because BV dominates VDS
etiology while the male (UDS) pathway should be mostly warranted.
Under POC, both should be near-zero false alarm.
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
    ('SOC', 'SOC'),
    ('POC_c-baseline_p-baseline_b-none', 'POC'),
    ('POC_c-high_p-baseline_b-none', 'POC+CS'),
    ('POC_c-baseline_p-high_b-none', 'POC+PN'),
    ('POC_c-baseline_p-baseline_b-high', 'POC+BP'),
]
WARRANTED_COLOR = '#3b86c4'
OVER_COLOR = '#e6772d'


def set_font(size=9):
    if Path(FONT).exists():
        sc.fonts(add=FONT)
        sc.options(font='Libertinus Sans', fontsize=size)
    else:
        sc.options(fontsize=size)


def _agg(kavg, col):
    out = []
    for cell, _ in CELL_ORDER:
        out.append(kavg.loc[kavg.cell == cell, col].median() / 1e6 if col in kavg.columns else 0.0)
    return np.array(out)


def _stacked_panel(ax, totals, over_part, title, ylabel=None,
                   over_label='over', warranted_label='warranted',
                   show_pct=True):
    x = np.arange(len(CELL_ORDER))
    warranted = totals - over_part
    ax.bar(x, warranted, color=WARRANTED_COLOR, alpha=0.95, label=warranted_label)
    ax.bar(x, over_part, bottom=warranted, color=OVER_COLOR, alpha=0.95, label=over_label)
    if show_pct:
        for i, (o, t) in enumerate(zip(over_part, totals)):
            if t > 0:
                ax.text(i, t * 1.02, f'{o / t * 100:.0f}%',
                        ha='center', va='bottom', fontsize=7, color=OVER_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in CELL_ORDER], fontsize=7.5)
    if totals.max() > 0:
        ax.set_ylim(bottom=0, top=totals.max() * 1.20)
    ax.tick_params(axis='y', labelsize=7.5)
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_title(title, fontsize=10, pad=4)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)
    ax.legend(fontsize=7, frameon=False, loc='upper left')


def _row(axes, kavg, idx_sex, partner_sex, label_idx, label_partner):
    """One row of the cascade for a given index sex."""
    idx_total = _agg(kavg, f'pn_new_index_total_{idx_sex}')
    idx_over = _agg(kavg, f'pn_new_index_no_sti_{idx_sex}')
    not_total = _agg(kavg, f'pn_new_notified_{partner_sex}')
    att_total = _agg(kavg, f'pn_new_attending_{partner_sex}')
    att_no_sti = _agg(kavg, f'pn_new_attended_no_sti_{partner_sex}')

    # Approximate notification-over via the index over fraction for this sex.
    with np.errstate(divide='ignore', invalid='ignore'):
        over_frac = np.where(idx_total > 0, idx_over / idx_total, 0.0)
    not_over = not_total * over_frac

    _stacked_panel(axes[0], idx_total, idx_over,
                   title=f'(i) {label_idx} indexes (PN triggers)',
                   ylabel='cumulative 2027-40\n(millions)',
                   over_label=f'{label_idx} had no STI',
                   warranted_label=f'{label_idx} had STI')

    _stacked_panel(axes[1], not_total, not_over,
                   title=f'(iii) {label_partner} partners notified',
                   over_label='index had no STI (approx)',
                   warranted_label='index had STI (approx)')

    _stacked_panel(axes[2], att_total, att_no_sti,
                   title=f'(iv) {label_partner} partners attended',
                   over_label=f'{label_partner} had no STI',
                   warranted_label=f'{label_partner} had STI')


def main():
    set_font(9)
    kavg = pd.read_csv(KAVG)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = pl.subplots(2, 3, figsize=(13, 8.5))
    _row(axes[0], kavg, idx_sex='f', partner_sex='m',
         label_idx='Female', label_partner='Male')
    _row(axes[1], kavg, idx_sex='m', partner_sex='f',
         label_idx='Male', label_partner='Female')

    fig.text(0.5, 0.96, 'Female-index pathway (VDS-triggered)',
             ha='center', fontsize=11, fontweight='bold', color='#444')
    fig.text(0.5, 0.485, 'Male-index pathway (UDS-triggered)',
             ha='center', fontsize=11, fontweight='bold', color='#444')

    fig.text(0.5, 0.012,
             'Validation: 5 cells x 5 draws (exp 06 top 5) x K=5 seeds; per-cell median across draws. '
             'Each row is the cascade triggered by one index sex; opposite-sex partners are notified/attend. '
             '(iii) "warranted vs over" propagates the index warrant fraction through notifications (notify rate '
             'is assumed STI-agnostic). (iv) splits by partner STI status (direct).',
             ha='center', fontsize=6.6, color='#666')
    fig.subplots_adjust(left=0.075, right=0.99, top=0.92, bottom=0.085,
                        wspace=0.32, hspace=0.5)
    out = FIG_DIR / 'fig_validation_pn_cascade.png'
    fig.savefig(out, dpi=200)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()