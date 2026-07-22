"""Slide 14: 4-panel heatmap — percent reduction in unnecessary F->M partner notification vs SOC.

Panels: BP = none / low / moderate / high.
Each panel: care-seeking (rows, baseline at bottom) x PN intensity (cols) heatmap.

Cell metric per (cell, draw): the *rate* at which female PN indexes had no STI
= ``pn_new_index_no_sti_f / pn_new_index_total_f``. Under SOC every VDS woman
triggers PN regardless of etiology; under POC, PN is triggered only after
etiological confirmation. Rate framing (rather than raw counts) isolates POC's
diagnostic-accuracy story from PN-intensity volume — at high PN intensity,
partner-cascade treatments (empirically treated partners) also count as
indexes, so absolute no-STI-index counts can go up even as the rate goes down.
Reduction = 100 * (SOC_median_rate - cell_median_rate) / SOC_median_rate.

    conda run -n starsim python plot_slide14.py
"""
from __future__ import annotations

import pandas as pd

from plot_slide12 import (KAVG, REPO,
                          cell_median_pct_reduction, draw_heatmap_grid)


def main():
    kavg = pd.read_csv(KAVG)
    arm_pct = cell_median_pct_reduction(
        kavg,
        lambda df: df['pn_new_index_no_sti_f'] / df['pn_new_index_total_f'],
    )
    draw_heatmap_grid(
        arm_pct,
        cbar_label='Reduction vs SOC (%)\nrate of female PN indexes without STI\n(no_sti_f / total_f), 2027–2040',
        out_png=REPO / 'figures' / 'fig_slide14.png',
        # Small negative reductions are model noise (single-digit %); censor
        # them to grey "No change" so the sequential cmap covers just the
        # policy-meaningful positive range.
        censor_negative=True,
    )


if __name__ == '__main__':
    main()
