"""Story figures from the exp 08 ensemble (26 draws): the PN ladder and the
bundled-prevention ladder, each as CT prevalence + CT incidence vs intensity,
ensemble median with IQR band. House style, 9.7w x 5h, no secondary axes.

  fig_pn_story.png  - POC + PN lowers prevalence but incidence stays high (reinfection)
  fig_bp_story.png  - adding bundled prevention lowers BOTH prevalence and incidence
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

HERE = Path(__file__).resolve().parent
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'
YEARS = 2040 - 2027

BLUE = '#4a90d9'   # prevalence
RED = '#c0504d'    # incidence

PN = (['POC_pn_baseline', 'POC_pn_low', 'POC_pn_moderate', 'POC_pn_high', 'POC_pn_maximum'],
      ['baseline', 'low', 'moderate', 'high', 'maximum'], 'partner notification intensity')
BP = (['POC_pn_baseline', 'POC_bp_low', 'POC_bp_moderate', 'POC_bp_high', 'POC_bp_maximum'],
      ['none', 'low', 'moderate', 'high', 'maximum'], 'bundled prevention coverage')


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def load():
    rows = [json.loads(l) for l in (HERE / 'outputs' / 'results.jsonl').read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    return df[df.get('status', 'ok') == 'ok'].copy()


def band(df, cells, col, scale=1.0):
    g = df[df.cell.isin(cells)].groupby('cell')[col]
    med = (g.median() * scale).reindex(cells).values
    lo = (g.quantile(0.25) * scale).reindex(cells).values
    hi = (g.quantile(0.75) * scale).reindex(cells).values
    return med, lo, hi


def make(df, ladder, title, subtitles, footnote, fname, compare=None, main_label=None):
    cells, xlabels, xlab = ladder
    x = np.arange(len(cells))
    ndraws = df.draw.nunique()

    fig, (axp, axi) = pl.subplots(1, 2, figsize=(9.7, 5))

    for ax, col, scale, color, ylab, sub in [
        (axp, 'ct_prev_end', 1.0, BLUE, 'CT prevalence, 2040', subtitles[0]),
        (axi, 'ct_new_inf', 1e-6 / YEARS, RED, 'CT new infections per year (millions)', subtitles[1]),
    ]:
        med, lo, hi = band(df, cells, col, scale)
        ax.fill_between(x, lo, hi, color=color, alpha=0.18, zorder=1)
        ax.plot(x, med, 'o-', color=color, lw=2, ms=6, zorder=3,
                label=main_label)
        if compare is not None:
            ccells, clabel = compare
            cmed, _, _ = band(df, ccells, col, scale)
            ax.plot(x, cmed, '^--', color='#888888', lw=1.6, ms=5, zorder=2,
                    label=clabel)
        ax.set_xticks(x)
        ax.set_xticklabels(xlabels, fontsize=9)
        ax.set_xlabel(xlab, fontsize=9.5)
        ax.set_ylabel(ylab, fontsize=9.5)
        ax.set_title(sub, fontsize=11, color=color, pad=8)
        ax.set_ylim(bottom=0)
        ax.tick_params(axis='y', labelsize=8.5)
        ax.margins(x=0.06)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if compare is not None:
            ax.legend(fontsize=8, frameon=False, loc='upper right')

    fig.text(0.5, 0.955, title, ha='center', fontsize=13)
    fig.text(0.5, 0.03, footnote.format(ndraws=ndraws), ha='center',
             fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.085, right=0.985, top=0.86, bottom=0.21, wspace=0.28)
    (HERE / 'figures').mkdir(exist_ok=True)
    p = HERE / 'figures' / fname
    fig.savefig(p, dpi=200)
    print('wrote', p)


def main():
    set_font(11)
    df = load()

    make(df, PN,
         'Partner notification lowers prevalence more than incidence',
         ('Prevalence falls steeply', 'Incidence falls less'),
         'POC diagnostic arm, ensemble median and IQR across {ndraws} calibrated draws. Scaling partner '
         'notification\nroughly halves prevalence but reduces incidence less: reinfection through ongoing '
         'partnerships blunts the effect on transmission. Indicative: ensemble predates the BV-in-VDS edit.',
         'fig_pn_story.png')

    make(df, BP,
         'Adding bundled prevention lowers both prevalence and incidence',
         ('Prevalence falls', 'Incidence falls'),
         'POC diagnostic arm, baseline partner notification, ensemble median and IQR across {ndraws} draws. '
         'Bundled prevention\n(condoms plus counselling for the diagnosed) reduces susceptibility, so both '
         'prevalence and incidence decline. Grey dashed = scaling partner notification instead, for comparison. '
         'Indicative: predates the BV-in-VDS edit.',
         'fig_bp_story.png',
         compare=(PN[0], 'scale partner notification'),
         main_label='add bundled prevention')


if __name__ == '__main__':
    main()
