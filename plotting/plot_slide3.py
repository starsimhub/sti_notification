"""Slide 3: SOC baseline overtreatment + over-notification for VDS women.

Problem-statement figure (SOC only, no POC comparison here -- that comes at
Slide 5). Three regions:

  Top strip (4 mini-panels): % of SOC women treated for {NG, CT, TV, syph}
      who don't have that pathogen. Sourced from scenarios.kavg.csv.

  Bottom-left (main panel): the "upset-riff" -- for every woman fronting up
      for VDS, how many drugs did she receive (0/1/2/3) and how many
      infections did she actually have. Stacked bar chart. Sourced from
      soc_overtreatment.csv (SocOvertreatmentTracer output). Drugs counted:
      ng_tx, ct_tx, metronidazole. STIs counted: NG/CT/TV/syph (BV excluded).

  Bottom-right: unwarranted male-partner PN volume under SOC (small stacked
      bar, warranted vs unwarranted). Sourced from specificity.csv.

  conda run -n starsim python plot_slide3.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
from matplotlib.gridspec import GridSpec

REPO = Path(__file__).resolve().parent.parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
SPEC = REPO / 'results' / 'specificity.csv'
SOC_OT = REPO / 'results' / 'soc_overtreatment.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

# R1 palette. SOC = gray. STI-count stack: light -> dark grays with clearer
# separation than default so 0/1/2+ read distinctly.
SOC_C = '#555555'
STI_C = {0: '#e5b8b3', 1: '#a8a29e', 2: '#2c3e50'}  # 0 STIs = pale terracotta
                                                     # (highlight "over" segment)
                                                     # 1 STI = mid gray
                                                     # 2+ STIs = dark navy

DISEASES = [('ng', 'Gonorrhoea'), ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'), ('syph', 'Syphilis')]
SCALE = 8.7e6 / 1e4  # total_pop / n_agents -> people
YEARS = 2040 - 2027


def per_disease_over_panel(ax, k, disease, fs=10):
    """SOC-only bar: % of women treated for `disease` who don't have it."""
    tot = k.loc[k.cell == 'SOC', f'{disease}_new_treated_f'].to_numpy(float)
    un = k.loc[k.cell == 'SOC', f'{disease}_new_treated_unnecessary_f'].to_numpy(float)
    frac = 100 * np.median(un / np.where(tot > 0, tot, np.nan))
    ax.bar(0, frac, color=SOC_C, width=0.55, zorder=3)
    ax.text(0, frac + 2, f'{frac:.0f}%', ha='center', va='bottom',
            fontsize=fs + 1, color=SOC_C)
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(0, 118)  # extra headroom so 95%+ labels don't clip
    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=fs - 1)
    ax.spines[['top', 'right', 'bottom']].set_visible(False)


def upset_riff_panel(ax, ot, fs=11):
    """VDS women by (n_drugs, n_stis_bucket). Stacked-by-STI-count bars.

    n_drugs ∈ {0,1,2,3}; stack layers = 0, 1, 2+ STIs.
    Y-axis: VDS women per year, scaled to Zimbabwe pop, in millions.
    """
    grid = (ot.groupby(['n_drugs', 'n_stis_bucket', 'seed'])['count']
              .sum()
              .unstack('seed')
              .fillna(0))
    med = grid.median(axis=1) * SCALE / 1e6
    n_drugs_vals = sorted(ot.n_drugs.unique())
    n_stis_vals = [0, 1, 2]
    labels = {0: '0 STIs (fully unnecessary)',
              1: '1 STI',
              2: '2+ STIs'}
    x = np.arange(len(n_drugs_vals))
    bottoms = np.zeros(len(n_drugs_vals))
    totals = np.array([sum(med.get((nd, k), 0.0) for k in n_stis_vals)
                       for nd in n_drugs_vals])
    ymax = totals.max()
    for ns in n_stis_vals:
        heights = np.array([med.get((nd, ns), 0.0) for nd in n_drugs_vals])
        ax.bar(x, heights, bottom=bottoms, color=STI_C[ns], width=0.65,
               edgecolor='white', linewidth=0.8, zorder=3,
               label=labels[ns])
        for i, (h, tot) in enumerate(zip(heights, totals)):
            if tot > 0 and h / ymax > 0.03:
                pct = 100 * h / tot
                y = bottoms[i] + h / 2
                text_color = 'white' if ns == 2 else '#222'
                ax.text(x[i], y, f'{pct:.0f}%', ha='center', va='center',
                        fontsize=fs - 2, color=text_color, zorder=5)
        bottoms += heights
    # Total-count labels above each bar
    for i, tot in enumerate(totals):
        ax.text(x[i], tot + ymax * 0.02, f'{tot:.2f}M',
                ha='center', va='bottom', fontsize=fs - 2, color='#333')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{nd} drug{"s" if nd != 1 else ""}' for nd in n_drugs_vals],
                       fontsize=fs)
    ax.set_ylabel('VDS women / year (millions)', fontsize=fs)
    ax.set_title('Drugs received vs. actual STIs (SOC syndromic mgmt)',
                 fontsize=fs + 2, pad=8)
    ax.set_ylim(0, ymax * 1.18)
    ax.tick_params(axis='y', labelsize=fs - 2)
    ax.spines[['top', 'right']].set_visible(False)
    # Place legend above the plot area to avoid overlapping bars
    ax.legend(fontsize=fs - 1, frameon=False, loc='upper center',
              bbox_to_anchor=(0.5, -0.10), ncol=3, handlelength=1.2,
              handletextpad=0.5, columnspacing=1.5)


def pn_summary_panel(ax, s, fs=11):
    """SOC-only stacked bar: warranted vs unwarranted male-partner notifs."""
    d = s[s.arm == 'SOC']
    notif = d.pn_notified_m.to_numpy(float) * SCALE / 1e6
    ofrac = d.f_tx_over.to_numpy(float) / d.f_tx.to_numpy(float)
    tot_m = np.median(notif)
    over_m = np.median(notif * ofrac)
    warr_m = tot_m - over_m
    ax.bar(0, warr_m, color=SOC_C, width=0.55, zorder=3)
    ax.bar(0, over_m, bottom=warr_m, color=SOC_C, alpha=0.28, width=0.55,
           zorder=3)
    pct = 100 * over_m / tot_m if tot_m > 0 else 0
    ax.text(0, tot_m + tot_m * 0.05, f'{pct:.0f}%\nunwarranted',
            ha='center', va='bottom', fontsize=fs, color=SOC_C,
            linespacing=1.0)
    ax.set_xlim(-0.5, 0.5)
    ax.set_ylim(0, tot_m * 1.35)
    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=fs - 2)
    ax.set_ylabel('male-partner notifs / year (M)', fontsize=fs - 1)
    ax.set_title('...cascading into unwarranted PN', fontsize=fs + 2, pad=8)
    ax.spines[['top', 'right', 'bottom']].set_visible(False)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=12)
    k = pd.read_csv(KAVG)
    s = pd.read_csv(SPEC)
    ot = pd.read_csv(SOC_OT)

    # Cumulative counts -> per-year (already the case for kavg via YEARS
    # normalisation elsewhere; here we just scale ot into per-year millions
    # inside the upset panel).
    ot['count'] = ot['count'] / YEARS

    fig = pl.figure(figsize=(11.5, 7.2))
    outer = GridSpec(2, 6, figure=fig, height_ratios=[1, 2.6],
                     left=0.06, right=0.985, top=0.88, bottom=0.14,
                     hspace=0.75, wspace=0.55)

    # Top strip: 4 per-disease over% panels (columns 1-4 of the 6-wide grid;
    # leaves columns 0 and 5 empty so the top row doesn't span the full width)
    for i, (d, name) in enumerate(DISEASES):
        ax = fig.add_subplot(outer[0, i + 1])
        per_disease_over_panel(ax, k, d)
        ax.set_title(name, fontsize=10.5, pad=3)
        if i == 0:
            ax.set_ylabel('% treated for X\n but no X', fontsize=9,
                          labelpad=2)

    # Bottom: upset-riff (4 cols) + PN summary (2 cols wide) so PN isn't squished
    ax_ot = fig.add_subplot(outer[1, :4])
    upset_riff_panel(ax_ot, ot)

    ax_pn = fig.add_subplot(outer[1, 4:])
    pn_summary_panel(ax_pn, s)

    fig.suptitle('Syndromic management (SOC) generates substantial '
                 'overtreatment and unwarranted partner notification',
                 fontsize=13, y=0.96)
    fig.text(0.5, 0.03,
             'Top: median across draws from scenarios.kavg.csv (SOC cell), 2027–40, female indices. '
             'Bottom: SocOvertreatmentTracer (5 seeds, draw 263), 2027–40, VDS-presenting women; drugs '
             '= ng_tx / ct_tx / metronidazole; STIs = NG / CT / TV / syph (BV excluded).',
             ha='center', fontsize=8, color='#666666')

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_slide3.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
