"""Layering figures, average annual new infections over 2027-2040.

Mirror of plot_layering.py but reports incidence (mean annual new_infections
across the intervention window) instead of prevalence at 2040:

  figures/fig_layering_1way_newinf.png        each lever alone
  figures/fig_layering_cumulative_newinf.png  cumulative ladder
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent.parent
FIGS = REPO / 'figures'
TS = REPO / 'raw_results' / 'scenarios_timeseries.parquet'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

LEVELS = ['baseline', 'low', 'moderate', 'high']
BP = ['none', 'low', 'moderate', 'high']
XLAB = ['base', 'low', 'mod', 'high']
N_LEVELS = len(LEVELS)
DISEASES = ['ng', 'ct', 'tv', 'syph']
DNAME = {'ng': 'Gonorrhoea (NG)', 'ct': 'Chlamydia (CT)',
         'tv': 'Trichomoniasis (TV)', 'syph': 'Syphilis'}

CARE_C, PN_C, BP_C = '#4daf4a', '#4a90d9', '#f0b429'
SOC_C, POC_C = '#9aa0a6', '#2c3e50'

WINDOW = (2027, 2040)  # intervention window; inclusive


def cell(c='baseline', p='baseline', b='none'):
    return f'POC_c-{c}_p-{p}_b-{b}'


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def load():
    """Average annual new_infections over the intervention window, per cell, per disease."""
    ts = pd.read_parquet(TS)
    inc = {}
    n_years = WINDOW[1] - WINDOW[0] + 1
    for d in DISEASES:
        dd = ts[(ts.disease == d) & (ts.result_name == 'new_infections')
                & (ts.year >= WINDOW[0]) & (ts.year <= WINDOW[1])]
        # sum over years -> mean per year -> median across draws
        per_draw = dd.groupby(['cell', 'draw']).value.sum() / n_years
        inc[d] = per_draw.groupby('cell').median()
    return inc, ts.draw.nunique()


def ser(inc_d, cells):
    # rescale to thousands so axis labels stay clean
    return np.array([inc_d.get(c, np.nan) / 1000 for c in cells])


def panel(ax, inc_d, lines, dname):
    x = np.arange(N_LEVELS)
    soc, poc = inc_d['SOC'] / 1000, inc_d[cell()] / 1000
    ax.axhline(soc, color=SOC_C, ls='--', lw=1.1, zorder=1)
    ax.axhline(poc, color=POC_C, ls=':', lw=1.1, zorder=1)
    for lab, col, y, fillto in lines:
        ax.plot(x, y, 'o-', color=col, lw=1.9, ms=4.5, label=lab, zorder=3)
        if fillto is not None:
            ax.fill_between(x, y, fillto, color=col, alpha=0.13, zorder=2)
    ax.set_xticks(x); ax.set_xticklabels(XLAB, fontsize=8)
    ax.set_ylim(bottom=0); ax.margins(x=0.08, y=0.12)
    ax.tick_params(axis='y', labelsize=8)
    ax.set_title(dname, fontsize=10.5, pad=4)
    ax.spines[['top', 'right']].set_visible(False)


def figure(fname, lines_for, ref_labels, footnote, inc, ndraws):
    fig, axes = pl.subplots(2, 2, figsize=(9.7, 6.4))
    for ax, d in zip(axes.flat, DISEASES):
        panel(ax, inc[d], lines_for(inc[d]), DNAME[d])
    axes[0, 0].set_ylabel('mean annual new infections, 2027-2040 (thousands)', fontsize=9)
    axes[1, 0].set_ylabel('mean annual new infections, 2027-2040 (thousands)', fontsize=9)
    for ax in axes[1]:
        ax.set_xlabel('intervention intensity', fontsize=9)

    h, l = axes[0, 0].get_legend_handles_labels()
    ref = [pl.Line2D([], [], color=SOC_C, ls='--', lw=1.1, label=ref_labels[0]),
           pl.Line2D([], [], color=POC_C, ls=':', lw=1.1, label=ref_labels[1])]
    fig.legend(h + ref, l + [r.get_label() for r in ref], ncol=5, frameon=False,
               fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, 0.02, footnote, ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.09, right=0.99, top=0.9, bottom=0.11, wspace=0.22, hspace=0.28)
    out = FIGS / 'archive' / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print('wrote', out)


def main():
    set_font(11)
    inc, ndraws = load()

    def lines_1way(d_):
        return [('care-seeking', CARE_C, ser(d_, [cell(c=v) for v in LEVELS]), None),
                ('partner notification', PN_C, ser(d_, [cell(p=v) for v in LEVELS]), None),
                ('bundled prevention', BP_C, ser(d_, [cell(b=v) for v in BP]), None)]
    figure('fig_layering_1way_newinf.png', lines_1way, ('SOC', 'POC-plain'),
           f'POC arm, median of {ndraws} pilot draws. Mean annual new infections over 2027-2040 '
           '(intervention window). Each line scales one lever with the other two at baseline. '
           'Dashed = SOC, dotted = POC-plain.',
           inc, ndraws)

    def lines_cum(d_):
        pn = ser(d_, [cell(p=LEVELS[k]) for k in range(N_LEVELS)])
        pnbp = ser(d_, [cell(p=LEVELS[k], b=BP[k]) for k in range(N_LEVELS)])
        all3 = ser(d_, [cell(c=LEVELS[k], p=LEVELS[k], b=BP[k]) for k in range(N_LEVELS)])
        poc_top = np.full(N_LEVELS, d_[cell()] / 1000)
        return [('+ care-seeking', '#1b4f8a', all3, pnbp),
                ('+ bundled prevention', '#4a90d9', pnbp, pn),
                ('partner notification', '#9ecae1', pn, poc_top)]
    figure('fig_layering_cumulative_newinf.png', lines_cum, ('SOC', 'POC-plain'),
           f'POC arm, median of {ndraws} pilot draws. Mean annual new infections over 2027-2040. '
           'Levers added cumulatively; shaded bands = incremental contribution of each. '
           'Dashed = SOC, dotted = POC-plain.',
           inc, ndraws)


if __name__ == '__main__':
    main()
