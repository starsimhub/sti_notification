"""POC-alone story figure (CT, draw 726, baseline PN held fixed in both arms).

Story: switching syndromic management to POC etiological diagnostics improves
treatment precision (correct-treatment rate rises, unnecessary treatment falls
sharply) but, on its own, does not reduce prevalence or incidence.

3 panels, house style (Libertinus Sans), 9.7w x 5h, no secondary axes.
Reads outputs/poc_alone_results.json (from run.py).
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import sciris as sc
import matplotlib.pyplot as pl

HERE = Path(__file__).resolve().parent
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

GREY = '#9aa0a6'   # SOC
BLUE = '#4a90d9'   # POC
ARMS = ['SOC', 'POC']
ARM_C = {'SOC': GREY, 'POC': BLUE}
YEARS = 2040 - 2027   # window 2027-2040; annualize cumulative flows over the elapsed span


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def main():
    set_font(11)
    res = json.loads((HERE / 'outputs' / 'poc_alone_results.json').read_text())
    a = res['arms']

    fig, axes = pl.subplots(1, 3, figsize=(9.7, 5))
    x = np.arange(2)

    # Panel 1: treatment composition, stacked to true total, in millions.
    # appropriate = patient was infected (total - unnecessary); unnecessary = no infection.
    ax = axes[0]
    total = np.array([a[k]['ct_tx_total'] for k in ARMS]) / 1e6 / YEARS
    unnec = np.array([a[k]['ct_tx_unnecessary'] for k in ARMS]) / 1e6 / YEARS
    approp = total - unnec
    for i, k in enumerate(ARMS):
        c = ARM_C[k]
        ax.bar(x[i], approp[i], color=c, width=0.62, zorder=3)
        ax.bar(x[i], unnec[i], bottom=approp[i], color=c, alpha=0.28,
               width=0.62, zorder=3)
        rate = 100 * approp[i] / total[i]
        ax.text(x[i], total[i] + total.max() * 0.04, f'{rate:.0f}% appropriate',
                ha='center', fontsize=9, color=c)
    ax.set_ylabel('CT treatments per year (millions)', fontsize=9.5)
    ax.set_title('POC improves treatment precision', fontsize=11, color=BLUE, pad=8)
    # direct-label the SOC bar segments (clearer than a floating legend)
    ax.text(0, approp[0] / 2, 'patient\ninfected', ha='center', va='center',
            fontsize=8, color='white')
    ax.text(0, approp[0] + unnec[0] / 2, 'unnecessary', ha='center', va='center',
            fontsize=8, color='#555555')

    # Panel 2: prevalence (window mean) - unchanged
    ax = axes[1]
    prev = np.array([a[k]['ct_prev_mean'] for k in ARMS])
    ax.bar(x, prev, color=[ARM_C[k] for k in ARMS], width=0.62, zorder=3)
    for i in range(2):
        ax.text(x[i], prev[i] + prev.max() * 0.02, f'{prev[i]:.3f}',
                ha='center', fontsize=9, color=ARM_C[ARMS[i]])
    ax.set_ylabel('CT prevalence, 2030-34 mean', fontsize=9.5)
    ax.set_title('Prevalence not reduced', fontsize=11, color='#666666', pad=8)

    # Panel 3: incidence - unchanged
    ax = axes[2]
    inc = np.array([a[k]['ct_inc'] for k in ARMS]) / 1e6 / YEARS
    ax.bar(x, inc, color=[ARM_C[k] for k in ARMS], width=0.62, zorder=3)
    for i in range(2):
        ax.text(x[i], inc[i] + inc.max() * 0.02, f'{inc[i]:.1f}M',
                ha='center', fontsize=9, color=ARM_C[ARMS[i]])
    ax.set_ylabel('CT new infections per year (millions)', fontsize=9.5)
    ax.set_title('Incidence not reduced', fontsize=11, color='#666666', pad=8)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(ARMS, fontsize=10)
        ax.set_ylim(bottom=0)
        ax.margins(y=0.18)
        ax.tick_params(axis='y', labelsize=8.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.text(0.5, 0.035,
             'Single calibrated draw (726), baseline partner notification held fixed in both arms. POC raises the '
             'share of treatments\ngiven to infected patients (53% to 88%) and cuts unnecessary treatment sharply, '
             'but prevalence and incidence are unchanged.',
             ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.985, top=0.93, bottom=0.19, wspace=0.34)

    (HERE / 'figures').mkdir(exist_ok=True)
    p = HERE / 'figures' / 'fig_poc_alone.png'
    fig.savefig(p, dpi=200)  # no bbox trim: keep exactly 9.7x5
    print('wrote', p)


if __name__ == '__main__':
    main()
