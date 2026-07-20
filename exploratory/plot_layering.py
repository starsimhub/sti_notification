"""Layering figures from the scenario factorial (results/scenarios_timeseries.parquet).

Multi-disease small multiples (NG/CT/TV/syph), prevalence at 2040, median over the
pilot draws, with SOC and POC-plain references:

  figures/fig_layering_1way.png        each lever alone (care-seeking / PN / bundled prev)
  figures/fig_layering_cumulative.png  ladder up: PN -> PN+BP -> PN+BP+care-seeking

House style; no figure titles (per-panel disease subtitles + shared legend + footnote).
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


def cell(c='baseline', p='baseline', b='none'):
    return f'POC_c-{c}_p-{p}_b-{b}'


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def load():
    ts = pd.read_parquet(TS)
    prev = {}
    for d in DISEASES:
        dd = ts[(ts.disease == d) & (ts.result_name == 'prevalence') & (ts.year == 2040)]
        prev[d] = dd.groupby('cell').value.median()
    return prev, ts.draw.nunique()


def ser(prev_d, cells):
    return np.array([prev_d.get(c, np.nan) * 100 for c in cells])


def panel(ax, prev_d, lines, dname):
    x = np.arange(N_LEVELS)
    soc, poc = prev_d['SOC'] * 100, prev_d[cell()] * 100
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


def figure(fname, lines_for, ref_labels, footnote, prev, ndraws):
    fig, axes = pl.subplots(2, 2, figsize=(9.7, 6.4))
    for ax, d in zip(axes.flat, DISEASES):
        panel(ax, prev[d], lines_for(prev[d]), DNAME[d])
    axes[1, 0].set_ylabel('prevalence, 2040 (%)', fontsize=9.5)
    axes[0, 0].set_ylabel('prevalence, 2040 (%)', fontsize=9.5)
    for ax in axes[1]:
        ax.set_xlabel('intervention intensity', fontsize=9)

    # shared legend: lever lines (from a panel) + SOC/POC reference styles
    h, l = axes[0, 0].get_legend_handles_labels()
    ref = [pl.Line2D([], [], color=SOC_C, ls='--', lw=1.1, label=ref_labels[0]),
           pl.Line2D([], [], color=POC_C, ls=':', lw=1.1, label=ref_labels[1])]
    fig.legend(h + ref, l + [r.get_label() for r in ref], ncol=5, frameon=False,
               fontsize=8.5, loc='upper center', bbox_to_anchor=(0.5, 1.0))
    fig.text(0.5, 0.02, footnote, ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.11, wspace=0.18, hspace=0.28)
    out = FIGS / 'archive' / fname
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print('wrote', out)


def main():
    set_font(11)
    prev, ndraws = load()

    # L1: each lever alone, others at baseline
    def lines_1way(pd_):
        return [('care-seeking', CARE_C, ser(pd_, [cell(c=v) for v in LEVELS]), None),
                ('partner notification', PN_C, ser(pd_, [cell(p=v) for v in LEVELS]), None),
                ('bundled prevention', BP_C, ser(pd_, [cell(b=v) for v in BP]), None)]
    figure('fig_layering_1way.png', lines_1way, ('SOC', 'POC-plain'),
           f'POC arm, median of {ndraws} pilot draws. Each line scales one lever with the other two at baseline '
           '(all start at POC-plain). Dashed = SOC, dotted = POC-plain.',
           prev, ndraws)

    # L2: cumulative ladder PN -> +BP -> +care-seeking
    def lines_cum(pd_):
        pn = ser(pd_, [cell(p=LEVELS[k]) for k in range(N_LEVELS)])
        pnbp = ser(pd_, [cell(p=LEVELS[k], b=BP[k]) for k in range(N_LEVELS)])
        all3 = ser(pd_, [cell(c=LEVELS[k], p=LEVELS[k], b=BP[k]) for k in range(N_LEVELS)])
        poc_top = np.full(N_LEVELS, pd_[cell()] * 100)
        return [('+ care-seeking', '#1b4f8a', all3, pnbp),
                ('+ bundled prevention', '#4a90d9', pnbp, pn),
                ('partner notification', '#9ecae1', pn, poc_top)]
    figure('fig_layering_cumulative.png', lines_cum, ('SOC', 'POC-plain'),
           f'POC arm, median of {ndraws} pilot draws. Levers added cumulatively as intensity scales; '
           'shaded bands = incremental contribution of each. Dashed = SOC, dotted = POC-plain.',
           prev, ndraws)


if __name__ == '__main__':
    main()
