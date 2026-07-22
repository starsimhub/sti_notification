"""Slide 12: 4-panel heatmap — percent reduction in cumulative STI infections vs SOC.

Panels: BP = none / low / moderate / high.
Each panel: care-seeking (rows, baseline at bottom) x PN intensity (cols) heatmap.
Cells: (SOC_median - cell_median) / SOC_median * 100, where each cell's total
is the sum of window-cumulative new_infections across 4 curable STIs
(NG + CT + TV + syph) and the median is across draws.

Also exports ``draw_heatmap_grid`` — the shared 4-panel drawing helper — for
use by slides 13 (overtreatment) and 14 (unnecessary F->M PN), which read the
same K-avg CSV and only differ in the per-arm scalar they compute.

    conda run -n starsim python plot_slide12.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as pl
import numpy as np
import pandas as pd
import sciris as sc

REPO = Path(__file__).resolve().parents[1]
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
FONT = str(REPO / 'assets' / 'LibertinusSans-Regular.otf')

DISEASES = ('ng', 'ct', 'tv', 'syph')
CARE_LEVELS = ('baseline', 'low', 'moderate', 'high')
PN_LEVELS = ('baseline', 'low', 'moderate', 'high')
BP_PANELS = ('none', 'low', 'moderate', 'high')


def cell_median_pct_reduction(kavg, per_draw_metric):
    """Given kavg (per (cell, draw) scalars) and a callable that returns the
    per-draw metric for a row, compute median across draws per cell then the
    percent reduction of each POC arm vs SOC.

    Returns a DataFrame with columns [care, pn, bp, pct_reduction].
    """
    df = kavg.copy()
    df['metric'] = per_draw_metric(df)
    cell_med = df.groupby(['cell', 'care', 'pn', 'bp'], dropna=False)['metric'].median()
    soc_med = float(cell_med.loc['SOC'].iloc[0])
    poc = (cell_med.reset_index()
                    .query('cell != "SOC"')
                    .assign(pct_reduction=lambda d: 100.0 * (soc_med - d['metric']) / soc_med))
    return poc[['care', 'pn', 'bp', 'pct_reduction']]


def draw_heatmap_grid(arm_pct, cbar_label, out_png, censor_negative=False):
    """4-panel heatmap: care x PN (rows x cols), one panel per BP level.

    arm_pct: DataFrame with columns [care, pn, bp, pct_reduction], one row per
    POC arm (typically 64 rows: 4 x 4 x 4 factorial).
    cbar_label: multi-line label for the shared colorbar.
    out_png: destination Path for the figure PNG.
    censor_negative: when True, values < 0 are drawn in grey and labelled
    "No change" (the colorbar is clamped to [0, vmax] with a sequential cmap).
    Use for metrics where a negative "reduction" is small model noise and would
    otherwise dominate the diverging colour scale.
    """
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    fig, axes = pl.subplots(1, 4, figsize=(12, 5),
                            gridspec_kw=dict(wspace=0.15))

    vmin = float(arm_pct['pct_reduction'].min())
    vmax = float(arm_pct['pct_reduction'].max())
    if censor_negative:
        vmin, cmap = 0.0, 'viridis'
    elif vmin < 0:
        # Diverging cmap centered on 0 if any negatives.
        m = max(abs(vmin), abs(vmax))
        vmin, vmax, cmap = -m, m, 'RdBu_r'
    else:
        cmap = 'viridis'
    cmap_obj = pl.get_cmap(cmap).copy()
    cmap_obj.set_bad(color='#cccccc')

    grids = []
    for bp in BP_PANELS:
        sub = arm_pct[arm_pct.bp == bp]
        g = (sub.pivot_table(index='care', columns='pn', values='pct_reduction')
                .reindex(index=CARE_LEVELS, columns=PN_LEVELS))
        grids.append(g)

    for i_ax, (ax, bp, g) in enumerate(zip(axes, BP_PANELS, grids)):
        # origin='lower' puts row 0 (baseline care) at the bottom so care-seeking
        # increases as the eye moves upward.
        arr = g.to_numpy()
        # When censoring, mask negatives so they render with the "bad" colour.
        plot_arr = np.ma.masked_where(arr < 0, arr) if censor_negative else arr
        im = ax.imshow(plot_arr, cmap=cmap_obj, vmin=vmin, vmax=vmax,
                       aspect='auto', origin='lower')
        ax.set_xticks(range(len(PN_LEVELS)))
        ax.set_xticklabels(PN_LEVELS)
        ax.set_yticks(range(len(CARE_LEVELS)))
        if i_ax == 0:
            ax.set_yticklabels(CARE_LEVELS)
        else:
            ax.set_yticklabels([])
        ax.set_xlabel('Partner notification')
        ax.set_title(f'Bundled prevention: {bp}', fontsize=11)
        # Cell text: pick colour from the underlying rgba's luminance so it
        # stays readable across the full colormap (viridis is dark at low
        # values, bright yellow at high). Censored (grey) cells get "No change".
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                v = g.iat[i, j]
                if np.isnan(v):
                    continue
                if censor_negative and v < 0:
                    ax.text(j, i, 'No change', ha='center', va='center',
                            fontsize=8, color='#555555')
                    continue
                norm = (v - vmin) / (vmax - vmin) if vmax > vmin else 0.5
                r, gr, b, _ = cmap_obj(norm)
                lum = 0.299 * r + 0.587 * gr + 0.114 * b
                textc = 'black' if lum > 0.55 else 'white'
                ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                        fontsize=9, color=textc)
    axes[0].set_ylabel('Care-seeking')

    cbar = fig.colorbar(im, ax=axes, orientation='vertical', shrink=0.85,
                        pad=0.02, fraction=0.03)
    cbar.set_label(cbar_label, fontsize=9)

    out_png.parent.mkdir(exist_ok=True)
    fig.savefig(out_png, dpi=200, bbox_inches='tight')
    print(f'wrote {out_png}')


def main():
    kavg = pd.read_csv(KAVG)
    arm_pct = cell_median_pct_reduction(
        kavg,
        lambda df: df[[f'{d}_new_inf' for d in DISEASES]].sum(axis=1),
    )
    draw_heatmap_grid(
        arm_pct,
        cbar_label='Reduction vs SOC (%)\ncum. NG+CT+TV+syph infections 2027–2040',
        out_png=REPO / 'figures' / 'fig_slide12.png',
    )


if __name__ == '__main__':
    main()
