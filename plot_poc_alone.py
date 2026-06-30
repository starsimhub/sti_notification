"""POC-alone story figure, multi-disease (NG/CT/TV/syph). Slide format.

Story: switching syndromic management to POC etiological diagnostics improves
treatment precision (appropriate-treatment share rises, total/unnecessary
treatment falls) but, on its own, does not reduce prevalence or incidence --
and the same pattern repeats across every pathogen.

Layout: 3 metric rows x 4 disease columns, 12.15w x 5h (16:9 slide friendly).
  row 0  treatment precision   stacked bar (appropriate + unnecessary), SOC vs POC
  row 1  prevalence (2040)      SOC vs POC
  row 2  incidence (new inf/yr) SOC vs POC
Orienting text (the row message + unit) sits on the left; disease names are
column headers. Each cell is a SOC-vs-POC pair on its own axis.

Ensemble: SOC vs POC-plain across the 5 scenario draws (exp 06 top-5), baseline
PN held fixed in both arms. Bars = median across draws, whiskers = 25-75 IQR.
House style (Libertinus Sans), no figure title.

  conda run -n starsim python plot_poc_alone.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
import matplotlib.patches as mpatches

REPO = Path(__file__).resolve().parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

GREY, BLUE = '#9aa0a6', '#4a90d9'
ARMS = {'SOC': 'SOC', 'POC': 'POC_c-baseline_p-baseline_b-none'}
ARM_C = {'SOC': GREY, 'POC': BLUE}
DISEASES = [('ng', 'Gonorrhoea'), ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'), ('syph', 'Syphilis')]
YEARS = 2040 - 2027  # annualize cumulative 2027-40 flows
# (row message, message colour, unit) for the three metric rows
ROWS = [('POC improves\ntreatment precision', BLUE, 'treatments / yr\n(millions)'),
        ('Prevalence\nnot reduced', '#555555', 'prevalence\n(2040)'),
        ('Incidence\nnot reduced', '#555555', 'new infections / yr\n(millions)')]


def set_font(size=12):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def fmt_m(v):
    return f'{v:.1f}M' if v >= 0.1 else f'{v * 1e3:.0f}k'


def series(k, cell, col):
    return k.loc[k.cell == cell, col].to_numpy(dtype=float)


def med_iqr(vals):
    return np.median(vals), np.quantile(vals, 0.25), np.quantile(vals, 0.75)


def main():
    set_font(12)
    k = pd.read_csv(KAVG)
    arms = list(ARMS)
    x = np.arange(2)

    fig, axes = pl.subplots(3, len(DISEASES), figsize=(12.15, 5))

    for c, (d, dname) in enumerate(DISEASES):
        tot = {a: series(k, ARMS[a], f'{d}_new_treated') / 1e6 / YEARS for a in arms}
        un = {a: series(k, ARMS[a], f'{d}_new_treated_unnecessary') / 1e6 / YEARS for a in arms}
        app = {a: tot[a] - un[a] for a in arms}
        appct = {a: 100 * np.median(app[a] / np.where(tot[a] > 0, tot[a], np.nan)) for a in arms}
        prev = {a: series(k, ARMS[a], f'{d}_prev_end') for a in arms}
        inc = {a: series(k, ARMS[a], f'{d}_new_inf') / 1e6 / YEARS for a in arms}

        # row 0: treatment precision (stacked appropriate + unnecessary)
        ax = axes[0, c]
        tmax = max(np.median(tot[a]) for a in arms)
        for i, a in enumerate(arms):
            cc = ARM_C[a]
            am, um = np.median(app[a]), np.median(un[a])
            ax.bar(i, am, color=cc, width=0.6, zorder=3)
            ax.bar(i, um, bottom=am, color=cc, alpha=0.28, width=0.6, zorder=3)
            tm, q1, q3 = med_iqr(tot[a])
            ax.errorbar(i, tm, yerr=[[tm - q1], [q3 - tm]], fmt='none',
                        ecolor='#555', elinewidth=0.9, capsize=2.5, zorder=4)
            ax.text(i, q3 + tmax * 0.07, f'{appct[a]:.0f}%', ha='center',
                    va='bottom', fontsize=11, color=cc)
        if c == 0:
            h = [mpatches.Patch(facecolor='#888', edgecolor='none'),
                 mpatches.Patch(facecolor='#888', alpha=0.28, edgecolor='none')]
            ax.legend(h, ['infected', 'unnecessary'], fontsize=8.5, frameon=False,
                      loc='upper right', handlelength=1.0, handletextpad=0.4,
                      labelspacing=0.2, borderaxespad=0.2)

        # row 1: prevalence (2040 endpoint)
        ax = axes[1, c]
        pmax = max(np.median(prev[a]) for a in arms)
        for i, a in enumerate(arms):
            pm, q1, q3 = med_iqr(prev[a])
            ax.bar(i, pm, color=ARM_C[a], width=0.6, zorder=3)
            ax.errorbar(i, pm, yerr=[[pm - q1], [q3 - pm]], fmt='none',
                        ecolor='#555', elinewidth=0.9, capsize=2.5, zorder=4)
            ax.text(i, q3 + pmax * 0.07, f'{pm:.3f}', ha='center', va='bottom',
                    fontsize=10, color=ARM_C[a])

        # row 2: incidence (new infections / yr)
        ax = axes[2, c]
        imax = max(np.median(inc[a]) for a in arms)
        for i, a in enumerate(arms):
            im, q1, q3 = med_iqr(inc[a])
            ax.bar(i, im, color=ARM_C[a], width=0.6, zorder=3)
            ax.errorbar(i, im, yerr=[[im - q1], [q3 - im]], fmt='none',
                        ecolor='#555', elinewidth=0.9, capsize=2.5, zorder=4)
            ax.text(i, q3 + imax * 0.07, fmt_m(im), ha='center', va='bottom',
                    fontsize=10, color=ARM_C[a])

        axes[0, c].set_title(dname, fontsize=14, pad=18)
        for r in range(3):
            ax = axes[r, c]
            ax.set_xlim(-0.6, 1.6); ax.set_ylim(bottom=0)
            ax.margins(y=0.26)
            ax.set_xticks(x)
            ax.set_xticklabels(['SOC', 'POC'] if r == 2 else [], fontsize=11)
            ax.tick_params(axis='y', labelsize=9)
            ax.spines[['top', 'right']].set_visible(False)

    fig.subplots_adjust(left=0.165, right=0.99, top=0.85, bottom=0.10,
                        wspace=0.34, hspace=0.30)

    # left orienting text per row (message + unit), aligned to each row's centre
    for r, (msg, col, unit) in enumerate(ROWS):
        bb = axes[r, 0].get_position()
        yc = (bb.y0 + bb.y1) / 2
        fig.text(0.085, yc + 0.03, msg, ha='center', va='center', fontsize=13.5,
                 color=col, linespacing=1.15, fontweight='bold')
        fig.text(0.085, yc - 0.055, unit, ha='center', va='center', fontsize=10,
                 color='#555', linespacing=1.1)

    fig.text(0.58, 0.015,
             'Ensemble of 5 calibrated draws (exp 06 top-5), baseline PN fixed in both arms. '
             'Bars = median across draws, whiskers = 25-75 IQR.',
             ha='center', fontsize=8.5, color='#666666')

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_poc_alone.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
