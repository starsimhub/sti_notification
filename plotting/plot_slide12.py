"""Slide 12: 4-panel heatmap — percent reduction in cumulative STI infections vs SOC.

Panels: BP = none / low / moderate / high.
Each panel: care-seeking (rows, baseline at bottom) x PN intensity (cols) heatmap.
Cells: (SOC_total - cell_total) / SOC_total * 100, where the totals sum
median cumulative new_infections across 4 curable STIs (NG + CT + TV + syph)
over the intervention window 2027-2040.

    conda run -n starsim python plot_slide12.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as pl
import numpy as np
import pandas as pd
import sciris as sc

REPO = Path(__file__).resolve().parents[1]
TS = REPO / 'results' / 'scenarios_timeseries.parquet'
OUT_PNG = REPO / 'figures' / 'fig_slide12.png'
FONT = str(REPO / 'assets' / 'LibertinusSans-Regular.otf')

DISEASES = ('ng', 'ct', 'tv', 'syph')
CARE_LEVELS = ('baseline', 'low', 'moderate', 'high')
PN_LEVELS = ('baseline', 'low', 'moderate', 'high')
BP_PANELS = ('none', 'low', 'moderate', 'high')
WINDOW = (2027, 2040)


def cumulative_by_arm(df):
    """Sum median new_infections across 2027-2040 and across the 4 diseases,
    keyed by (cell, care, pn, bp, poc). Returns a DataFrame with one row per arm."""
    w = df[(df.result_name == 'new_infections')
           & (df.disease.isin(DISEASES))
           & (df.year >= WINDOW[0]) & (df.year <= WINDOW[1])]
    return (w.groupby(['cell', 'care', 'pn', 'bp', 'poc'], dropna=False)['median']
             .sum().reset_index(name='cum_inf'))


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    df = pd.read_parquet(TS)
    arm = cumulative_by_arm(df)
    soc_total = float(arm.loc[arm.cell == 'SOC', 'cum_inf'].iloc[0])
    poc = arm[arm.poc == True].copy()
    poc['pct_reduction'] = 100.0 * (soc_total - poc['cum_inf']) / soc_total

    fig, axes = pl.subplots(1, 4, figsize=(12, 5),
                            gridspec_kw=dict(wspace=0.15))
    # Shared color scale across panels so panel-to-panel comparisons work.
    vmin = float(poc['pct_reduction'].min())
    vmax = float(poc['pct_reduction'].max())
    # Symmetric-ish around 0 if any negatives, else just [0, vmax].
    if vmin < 0:
        m = max(abs(vmin), abs(vmax))
        vmin, vmax, cmap = -m, m, 'RdBu_r'
    else:
        cmap = 'viridis'

    grids = []
    for bp in BP_PANELS:
        sub = poc[poc.bp == bp]
        g = (sub.pivot_table(index='care', columns='pn', values='pct_reduction')
                .reindex(index=CARE_LEVELS, columns=PN_LEVELS))
        grids.append(g)

    for i_ax, (ax, bp, g) in enumerate(zip(axes, BP_PANELS, grids)):
        # origin='lower' puts row 0 (baseline care) at the bottom so care-seeking
        # increases as the eye moves upward.
        im = ax.imshow(g.to_numpy(), cmap=cmap, vmin=vmin, vmax=vmax,
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
        # Cell annotations. Text colour picked from the underlying rgba's luminance
        # so it stays readable across the whole colormap (viridis is dark at low
        # values, bright yellow at high — a single fixed colour won't work).
        cmap_obj = pl.get_cmap(cmap)
        for i in range(g.shape[0]):
            for j in range(g.shape[1]):
                v = g.iat[i, j]
                if np.isnan(v):
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
    cbar.set_label('Reduction vs SOC (%)\ncum. NG+CT+TV+syph infections 2027–2040',
                   fontsize=9)

    OUT_PNG.parent.mkdir(exist_ok=True)
    fig.savefig(OUT_PNG, dpi=200, bbox_inches='tight')
    print(f'wrote {OUT_PNG}')


if __name__ == '__main__':
    main()
