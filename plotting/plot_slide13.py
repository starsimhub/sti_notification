"""Slide 13: 4-panel heatmap — percent reduction in unnecessary treatments vs SOC.

Panels: BP = none / low / moderate / high.
Each panel: care-seeking (rows, baseline at bottom) x PN intensity (cols) heatmap.
Cell metric per (cell, draw): sum of ``new_treated_unnecessary`` across the 4
curable STIs (NG + CT + TV + syph), window-cumulative 2027-2040 (already
pre-summed in ``scenarios.kavg.csv``). Reduction = 100 * (SOC_median - cell_median) / SOC_median.

    conda run -n starsim python plot_slide13.py
"""
from __future__ import annotations

import pandas as pd

from plot_slide12 import (KAVG, DISEASES, REPO,
                          cell_median_pct_reduction, draw_heatmap_grid)


def main():
    kavg = pd.read_csv(KAVG)
    arm_pct = cell_median_pct_reduction(
        kavg,
        lambda df: df[[f'{d}_new_treated_unnecessary' for d in DISEASES]].sum(axis=1),
    )
    draw_heatmap_grid(
        arm_pct,
        cbar_label='Reduction vs SOC (%)\ncum. unnecessary NG+CT+TV+syph treatments 2027–2040',
        out_png=REPO / 'figures' / 'fig_slide13.png',
    )


if __name__ == '__main__':
    main()
