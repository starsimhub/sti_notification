"""Slide 13: summary of reductions under the optimistic-realistic scenario.

Baseline = SOC. Best-case = POC + care-seeking moderate + PN moderate +
bundled-prevention moderate (POC_c-moderate_p-moderate_b-moderate). Bars
show % reduction vs SOC baseline (positive = improvement; negative =
worse than SOC).

Metrics (top to bottom):
  Aggregate (across NG/CT/TV/syph):
    * Over-treatment                 sum of `_new_treated_unnecessary`
    * Over-notification              `pn_new_notified_no_sti`
    * Under-treatment                sum(new_inf - new_treated_success)
  Per-disease:
    * Prevalence (2040)              `{d}_prev_end`
    * Incidence (cum 2027-40)        `{d}_new_inf`

Under-notification is NOT shown -- would need a tracer extension we
didn't run. Noted in the caption.

  conda run -n starsim python plot_slide13.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent.parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

SOC_CELL = 'SOC'
BEST_CELL = 'POC_c-moderate_p-moderate_b-moderate'

DISEASES = [('ng', 'NG'), ('ct', 'CT'), ('tv', 'TV'), ('syph', 'Syph')]
# Green = reduction (good). Red = increase (worse). Neutral gray for zero.
BAR_GOOD = '#2f8f4f'
BAR_BAD = '#c1492b'


def med(df, cell, col):
    return float(np.median(df.loc[df.cell == cell, col]))


def pct_reduction(soc_val, best_val):
    """Positive when best_val < soc_val (SOC baseline reduced by best-case)."""
    if soc_val == 0:
        return 0.0
    return 100 * (soc_val - best_val) / soc_val


def gather_reductions(k):
    """Return list of dicts: {group, label, pct_reduction, soc_raw, best_raw}.

    Quality metrics (over-tx, over-notif, under-tx) are RATE reductions
    (proportion of events that are 'over' or 'under'), not absolute counts.
    A rate framing cancels the volume effect of dialling PN intensity up in
    the best-case cell -- otherwise 'over-notification' looks worse under
    POC-mmm because moderate PN scales volume up even though the per-notif
    quality is better.
    """
    rows = []
    # Aggregate over-treatment RATE: unnecessary / all_treated across NG/CT/TV/syph
    def sum_med(cell, col):
        return sum(med(k, cell, f'{d}_{col}') for d, _ in DISEASES)
    ot_soc = sum_med(SOC_CELL, 'new_treated_unnecessary') / sum_med(SOC_CELL, 'new_treated')
    ot_best = sum_med(BEST_CELL, 'new_treated_unnecessary') / sum_med(BEST_CELL, 'new_treated')
    rows.append(dict(group='aggregate',
                     label=f'Over-treatment ({ot_soc:.0%}→{ot_best:.0%})',
                     pct=pct_reduction(ot_soc, ot_best),
                     soc=ot_soc, best=ot_best, unit='rate'))
    # Over-notification: index-side false-alarm RATE (female index with no
    # STI / all female index PN triggers). Partner-side `notified_no_sti`
    # confounds with reduced background prev (POC-mmm reduces STI prev, so
    # more notified partners happen to be uninfected -- a good thing, not
    # a failure). Index-side captures the diagnostic-precision story
    # cleanly.
    on_soc = (med(k, SOC_CELL, 'pn_new_index_no_sti_f')
              / med(k, SOC_CELL, 'pn_new_index_total_f'))
    on_best = (med(k, BEST_CELL, 'pn_new_index_no_sti_f')
               / med(k, BEST_CELL, 'pn_new_index_total_f'))
    rows.append(dict(group='aggregate',
                     label=f'Over-notification ({on_soc:.0%}→{on_best:.0%})',
                     pct=pct_reduction(on_soc, on_best),
                     soc=on_soc, best=on_best, unit='rate'))
    # Under-treatment RATE: untreated_inf / new_inf
    ut_soc = ((sum_med(SOC_CELL, 'new_inf') - sum_med(SOC_CELL, 'new_treated_success'))
              / sum_med(SOC_CELL, 'new_inf'))
    ut_best = ((sum_med(BEST_CELL, 'new_inf') - sum_med(BEST_CELL, 'new_treated_success'))
               / sum_med(BEST_CELL, 'new_inf'))
    rows.append(dict(group='aggregate',
                     label=f'Under-treatment ({ut_soc:.0%}→{ut_best:.0%})',
                     pct=pct_reduction(ut_soc, ut_best),
                     soc=ut_soc, best=ut_best, unit='rate'))
    # Per-disease prev + inc
    for d, dname in DISEASES:
        sv = med(k, SOC_CELL, f'{d}_prev_end')
        bv = med(k, BEST_CELL, f'{d}_prev_end')
        rows.append(dict(group='prevalence', label=dname,
                         pct=pct_reduction(sv, bv), soc=sv, best=bv,
                         unit='prev'))
    for d, dname in DISEASES:
        sv = med(k, SOC_CELL, f'{d}_new_inf')
        bv = med(k, BEST_CELL, f'{d}_new_inf')
        rows.append(dict(group='incidence', label=dname,
                         pct=pct_reduction(sv, bv), soc=sv, best=bv,
                         unit='cum inf'))
    return rows


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=12)
    k = pd.read_csv(KAVG)
    rows = gather_reductions(k)

    # Layout: horizontal grouped bars, grouped by (aggregate / prev / inc).
    n = len(rows)
    fig, ax = pl.subplots(figsize=(11, 6.5))
    y_positions = []
    y = 0
    prev_group = None
    for r in rows:
        if prev_group is not None and r['group'] != prev_group:
            y -= 0.6  # gap between groups
        y -= 1
        y_positions.append(y)
        prev_group = r['group']
    y_positions = np.array(y_positions)

    pct_vals = np.array([r['pct'] for r in rows])
    colors = [BAR_GOOD if p >= 0 else BAR_BAD for p in pct_vals]
    ax.barh(y_positions, pct_vals, color=colors, height=0.75, zorder=3)

    # Value labels + row labels
    for yp, r, p in zip(y_positions, rows, pct_vals):
        offset = 1.5 if p >= 0 else -1.5
        ha = 'left' if p >= 0 else 'right'
        cc = BAR_GOOD if p >= 0 else BAR_BAD
        ax.text(p + offset, yp, f'{p:+.0f}%', ha=ha, va='center',
                fontsize=11, color=cc, fontweight='bold')

    # Group headers (aggregate / prevalence / incidence) placed in the left
    # margin using the y-axis transform so x=0 is the axes-left edge.
    group_labels = {'aggregate': 'Quality-of-care',
                    'prevalence': 'Prevalence (2040)',
                    'incidence': 'Incidence (cum 27–40)'}
    seen_groups = []
    for yp, r in zip(y_positions, rows):
        if r['group'] not in seen_groups:
            ax.text(-0.31, yp + 0.6, group_labels[r['group']],
                    ha='left', va='center', fontsize=10.5,
                    color='#333', fontweight='bold',
                    transform=ax.get_yaxis_transform())
            seen_groups.append(r['group'])

    ax.set_yticks(y_positions)
    ax.set_yticklabels([r['label'] for r in rows], fontsize=11)
    ax.axvline(0, color='#333', lw=0.9, zorder=2)
    xmin = min(pct_vals.min() * 1.25, -5)
    xmax = max(pct_vals.max() * 1.15, 100)
    ax.set_xlim(xmin, xmax)
    ax.set_xlabel('% reduction vs. SOC baseline (→ = better)', fontsize=11)
    ax.tick_params(axis='x', labelsize=10)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='x', ls=':', color='#ccc', lw=0.5, zorder=0)

    fig.suptitle('Optimistic-realistic scenario: reductions vs. SOC baseline',
                 fontsize=13.5, y=0.975)
    fig.text(0.5, 0.930,
             'Best-case = POC + care-seeking moderate + PN moderate + '
             'bundled prevention moderate.',
             ha='center', fontsize=9.5, color='#666', style='italic')
    fig.text(0.5, 0.02,
             'Values = median across 5 draws from scenarios.kavg.csv. '
             'Under-notification not directly instrumented in this run; would '
             'require a tracer extension.',
             ha='center', fontsize=8.5, color='#666666')
    fig.subplots_adjust(left=0.32, right=0.94, top=0.88, bottom=0.11)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_slide13.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
