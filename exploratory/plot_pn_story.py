"""Partner-notification story figure (SOC), 9.7w x 5h, from results/pn_story.json
+ results/pn_partner_counts.csv (diagnostics/pn_story.py).

Left:  annual distinct partner counts by sex (histogram) + median/mean text.
Right: where partner notification breaks under SOC -- under-notification (most
       index cases notify no partner) and the over-cascade (unnecessary
       treatment / notification / attendance, index had no STI).

House style, no figure title.  conda run -n starsim python plot_pn_story.py
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent.parent
FIGS = REPO / 'figures'
JSON = REPO / 'results' / 'pn_story.json'
PC = REPO / 'results' / 'pn_partner_counts.csv'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

F_COLOR, M_COLOR = '#d46e9c', '#4a90d9'
RED, AMBER, GREEN = '#c0392b', '#f0b429', '#4daf4a'
WARRANT, OVER = '#4a90d9', '#e08a3c'
MAXBIN = 7  # lump partner counts >= this


def set_font(size=10):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def main():
    set_font(10)
    st = json.loads(JSON.read_text())
    pc = pd.read_csv(PC)

    fig, (axh, axb) = pl.subplots(1, 2, figsize=(9.7, 5),
                                  gridspec_kw={'width_ratios': [1, 1.25]})

    # --- left: partner-count histogram by sex ---
    bins = np.arange(0, MAXBIN + 2)
    x = np.arange(MAXBIN + 1)
    w = 0.4
    for sex, off, col, lab in [('f', -w / 2, F_COLOR, 'female'), ('m', w / 2, M_COLOR, 'male')]:
        n = pc[pc.sex == sex].n.clip(upper=MAXBIN).values
        h, _ = np.histogram(n, bins=bins)
        axh.bar(x + off, 100 * h / h.sum(), w, color=col, alpha=0.85, label=lab)
    axh.set_xticks(x)
    axh.set_xticklabels([str(i) for i in range(MAXBIN)] + [f'{MAXBIN}+'], fontsize=8.5)
    axh.set_xlabel('distinct partners over 12 months', fontsize=9.5)
    axh.set_ylabel('% of adults 15-49', fontsize=9.5)
    axh.legend(fontsize=8.5, frameon=False, loc='upper right')
    med, mean = st['partner_median'], st['partner_mean']
    axh.text(0.97, 0.62,
             f"median  F {med['f']:.0f}   M {med['m']:.0f}\nmean    F {mean['f']:.1f}   M {mean['m']:.1f}",
             transform=axh.transAxes, ha='right', va='top', fontsize=9,
             bbox=dict(boxstyle='round,pad=0.4', fc='#f4f4f4', ec='#cccccc', lw=0.6))
    axh.spines[['top', 'right']].set_visible(False)
    axh.margins(y=0.12)

    # --- right: under-notification + over-cascade, horizontal stacked bars ---
    u = st['under']; ni = u['n_index']
    none_p, some_p, all_p = 100 * u['none'] / ni, 100 * u['some'] / ni, 100 * u['all'] / ni
    over_rows = [
        ('Treatments', st['overtx']['n_treated'], st['overtx']['n_treated_no_sti']),
        ('Notifications', st['over']['n_notified'], st['over']['n_notified_no_sti']),
        ('Attendances', st['over']['n_attended'], st['over']['n_attended_no_sti']),
    ]

    y_under = 4.2
    # under-notification bar (per treated index): none / some / all
    axb.barh(y_under, none_p, color=RED, label='none')
    axb.barh(y_under, some_p, left=none_p, color=AMBER, label='some')
    axb.barh(y_under, all_p, left=none_p + some_p, color=GREEN, label='all')
    axb.text(none_p / 2, y_under, f'{none_p:.0f}%', ha='center', va='center',
             fontsize=9, color='white', fontweight='bold')
    axb.text(100, y_under + 0.55, 'partners notified per treated index case',
             ha='right', va='bottom', fontsize=8.5, color='#444444')

    # over-cascade bars: warranted vs unnecessary (index had no STI)
    ys = [2.4, 1.4, 0.4]
    for (lab, tot, bad), y in zip(over_rows, ys):
        over_p = 100 * bad / max(tot, 1)
        axb.barh(y, 100 - over_p, color=WARRANT)
        axb.barh(y, over_p, left=100 - over_p, color=OVER)
        axb.text(100 - over_p / 2, y, f'{over_p:.0f}%', ha='center', va='center',
                 fontsize=8.5, color='white', fontweight='bold')
        axb.text(-1.5, y, lab, ha='right', va='center', fontsize=9)
    axb.text(-1.5, y_under, 'Index cases', ha='right', va='center', fontsize=9)
    axb.text(100, 2.4 + 0.55, 'of events under syndromic SOC: unnecessary (index had no STI)',
             ha='right', va='bottom', fontsize=8.5, color='#444444')

    # color keys in the clear band between the under bar and the over bars
    h1 = [pl.Rectangle((0, 0), 1, 1, color=c) for c in (RED, AMBER, GREEN)]
    leg1 = axb.legend(h1, ['notified none', 'some', 'all'], fontsize=7.5, frameon=False,
                      loc='center left', bbox_to_anchor=(0.0, 0.70), ncol=3, handletextpad=0.4,
                      columnspacing=1.0)
    axb.add_artist(leg1)
    h2 = [pl.Rectangle((0, 0), 1, 1, color=c) for c in (WARRANT, OVER)]
    axb.legend(h2, ['warranted', 'unnecessary'], fontsize=7.5, frameon=False,
               loc='center left', bbox_to_anchor=(0.62, 0.70), ncol=2, handletextpad=0.4,
               columnspacing=1.0)

    axb.set_xlim(0, 100); axb.set_ylim(-0.3, 5.2)
    axb.set_yticks([]); axb.set_xlabel('% ', fontsize=9.5)
    axb.spines[['top', 'right', 'left']].set_visible(False)

    fig.text(0.5, 0.015,
             f"SOC (syndromic) model, draw {st['draw']}, single seed. Partner counts {st['partner_win'][0]}; "
             f"notification/treatment over {st['pn_win'][0]}-{st['pn_win'][1]}. "
             'Under-notification (most index cases reach no partner) dominates; over-events are the syndromic false-positive burden.',
             ha='center', fontsize=7, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.985, top=0.95, bottom=0.16, wspace=0.32)
    p = FIGS / 'supplementary' / 'fig_pn_story_grounding.png'
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
