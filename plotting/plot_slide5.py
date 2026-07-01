"""Slide 5: POC diagnostics improve correct treatment rates but cannot
eliminate overtreatment or over-notification.

Reads out of Slide 3 (which established the SOC baseline problem) by adding
the POC comparison. Left grid is identical to plot_result1's left half;
right panel is the female-index -> male-partner notifications cascade,
computed from the person-level specificity.csv tracer output.

Layout (10.4 x 5.4):
  Left  — 6 mini-panels (2 cols x 3 rows), reused from plot_result1:
    rows 0-1: NG, CT, TV, Syph treatment precision (SOC vs POC)
    row  2:   Female VDS treatment, Female GUD treatment
  Right — Female-index -> male-partner notifications, warranted vs over,
          SOC vs POC. Same person-level "over" definition as R1.

  conda run -n starsim python plot_slide5.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

from plot_result1 import (precision_panel, specificity_panel,
                          ARMS, ARM_C, DISEASES, SCALE, YEARS, FONT)

REPO = Path(__file__).resolve().parent.parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
SPEC = REPO / 'results' / 'specificity.csv'
FIGS = REPO / 'figures'


def pn_cascade_panel(ax, s, fs=11):
    """Female index -> male-partner notifications: warranted + over stacked.

    Notification rate is STI-agnostic in pn.py, so we split total notifs
    (pn_notified_m) by the person-level female-index over fraction
    (f_tx_over / f_tx) from specificity.csv.
    """
    arms = ['SOC', 'POC']
    totals, overs = {}, {}
    for a in arms:
        d = s[s.arm == a]
        notif = d.pn_notified_m.to_numpy(float) * SCALE / 1e6 / YEARS
        ofrac = d.f_tx_over.to_numpy(float) / d.f_tx.to_numpy(float)
        totals[a] = notif
        overs[a] = notif * ofrac
    tmax = max(np.median(totals[a]) for a in arms)
    for i, a in enumerate(arms):
        tot, ov = totals[a], overs[a]
        wm, om = np.median(tot - ov), np.median(ov)
        cc = ARM_C[a]
        ax.bar(i, wm, color=cc, width=0.6, zorder=3)
        ax.bar(i, om, bottom=wm, color=cc, alpha=0.28, width=0.6, zorder=3)
        pct = 100 * np.median(ov / np.where(tot > 0, tot, np.nan))
        ax.text(i, wm + om + tmax * 0.04, f'{pct:.0f}%\nover',
                ha='center', va='bottom', fontsize=fs, color=cc, linespacing=1.0)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(arms, fontsize=fs)
    ax.set_ylim(0, tmax * 1.55)
    ax.set_xlim(-0.6, 1.6)
    ax.tick_params(axis='y', labelsize=fs - 2)
    ax.set_ylabel('notifications / year (M)', fontsize=fs - 1)
    ax.set_title('Female index → male-partner\nnotifications',
                 fontsize=fs + 1, pad=6)
    ax.spines[['top', 'right']].set_visible(False)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)
    k = pd.read_csv(KAVG)
    s = pd.read_csv(SPEC)

    fig = pl.figure(figsize=(11, 6.0))
    outer = GridSpec(1, 2, figure=fig, width_ratios=[6.2, 2.6],
                     left=0.055, right=0.985, top=0.94, bottom=0.08,
                     wspace=0.22)
    left_gs = GridSpecFromSubplotSpec(3, 2, subplot_spec=outer[0],
                                      hspace=0.65, wspace=0.42)

    # ---- Left: rows 0-1, treatment precision by disease ----
    for idx, (d_key, d_name) in enumerate(DISEASES):
        r, c = divmod(idx, 2)
        ax = fig.add_subplot(left_gs[r, c])
        precision_panel(ax, k, d_key)
        ax.set_title(d_name, fontsize=10.5, pad=3)
        if c == 0:
            ax.set_ylabel('tx / yr (M)', fontsize=9, labelpad=2)
        if r == 0:
            ax.set_ylim(top=2)
        if r == 1:
            ax.set_ylim(top=1)

    # ---- Left: row 2, female VDS + GUD treatment events ----
    ax_vds = fig.add_subplot(left_gs[2, 0])
    arms = ['SOC', 'POC']
    f_tot = {a: s[s.arm == a].f_tx.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    f_ov = {a: s[s.arm == a].f_tx_over.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    specificity_panel(ax_vds, f_tot, f_ov)
    ax_vds.set_title('Female VDS treatment', fontsize=10.5, pad=3)
    ax_vds.set_ylabel('events / yr (M)', fontsize=9, labelpad=2)

    ax_gud = fig.add_subplot(left_gs[2, 1])
    poc_cell = ARMS['POC']
    g_tot = {
        'SOC': k[k.cell == 'SOC']['syph_new_treated_f'].to_numpy(float) / 1e6 / YEARS,
        'POC': k[k.cell == poc_cell]['syph_new_treated_f'].to_numpy(float) / 1e6 / YEARS,
    }
    g_ov = {
        'SOC': k[k.cell == 'SOC']['syph_new_treated_unnecessary_f'].to_numpy(float) / 1e6 / YEARS,
        'POC': k[k.cell == poc_cell]['syph_new_treated_unnecessary_f'].to_numpy(float) / 1e6 / YEARS,
    }
    specificity_panel(ax_gud, g_tot, g_ov)
    ax_gud.set_title('Female GUD treatment', fontsize=10.5, pad=3)

    # ---- Right: female index -> male-partner PN cascade ----
    ax_pn = fig.add_subplot(outer[1])
    pn_cascade_panel(ax_pn, s)

    # Cascade arrow linking the treatment grid to the PN panel
    fig.text(0.678, 0.28, '→', ha='center', va='center', fontsize=26,
             color='#999')

    # Legend at the top of the right-hand PN panel (R1 style patches).
    h = [mpatches.Patch(facecolor='#888', edgecolor='none'),
         mpatches.Patch(facecolor='#888', alpha=0.28, edgecolor='none')]
    ax_pn.legend(h, ['warranted', 'unnecessary'], fontsize=9, frameon=False,
                 loc='upper right', ncol=1,
                 handlelength=1.0, handletextpad=0.4,
                 labelspacing=0.2)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_slide5.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
