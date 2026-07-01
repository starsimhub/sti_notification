"""Publication-friendly visualizations of VDS etiology (from results/vds_etiology.csv).

Three alternatives for showing the etiology of vaginal discharge among women:
  figures/fig_vds_upset.png   - UpSet: intersection sizes + presence matrix + set sizes
  figures/fig_vds_burden.png  - coinfection burden: mono vs multi, and each pathogen alone vs with others
  figures/fig_vds_cooccur.png - pairwise co-occurrence heatmap

House style (Libertinus Sans). No figure titles (per-axis subtitles + footnotes only).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
from matplotlib.gridspec import GridSpec

REPO = Path(__file__).resolve().parent.parent
FIGS = REPO / 'figures'
CSV = REPO / 'results' / 'vds_etiology.csv'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

PATHS = ['ng', 'ct', 'tv', 'bv']
NAMES = {'ng': 'NG', 'ct': 'CT', 'tv': 'TV', 'bv': 'BV'}
COMBOS = ['ng_only', 'ct_only', 'tv_only', 'bv_only', 'ng_ct', 'ng_tv', 'ng_bv',
          'ct_tv', 'ct_bv', 'tv_bv', 'ng_ct_tv', 'ng_ct_bv', 'ng_tv_bv',
          'ct_tv_bv', 'ng_ct_tv_bv']
BLUE = '#4a90d9'
DARK = '#2c3e50'
GREY = '#d7dbe0'


def members(combo):
    return [t for t in combo.split('_') if t in PATHS]


def load():
    d = dict(zip(*[pd.read_csv(CSV)[c] for c in ('metric', 'value')]))
    vds_prev = d['vds_prev']
    marg = {p: d[f'marg_{p}'] for p in PATHS}
    combo = {c: d[c] for c in COMBOS}
    return vds_prev, marg, combo


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def upset(vds_prev, marg, combo):
    rows = sorted(PATHS, key=lambda p: marg[p])           # smallest at bottom
    cols = [c for c in sorted(COMBOS, key=lambda c: combo[c], reverse=True) if combo[c] > 0]
    n = len(cols)

    fig = pl.figure(figsize=(9.7, 5))
    gs = GridSpec(2, 2, width_ratios=[0.85, 5], height_ratios=[2.6, 1.5],
                  hspace=0.08, wspace=0.20, left=0.08, right=0.995, top=0.985, bottom=0.13)
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_mat = fig.add_subplot(gs[1, 1], sharex=ax_bar)
    ax_set = fig.add_subplot(gs[1, 0], sharey=ax_mat)

    x = np.arange(n)
    vals = [combo[c] * 100 for c in cols]
    ax_bar.bar(x, vals, color=BLUE, width=0.62)
    for xi, v in zip(x, vals):
        ax_bar.text(xi, v + 0.7, f'{v:.0f}', ha='center', fontsize=7.5, color=DARK)
    ax_bar.set_ylabel('% of VDS women', fontsize=9.5)
    ax_bar.set_ylim(0, max(vals) * 1.16)
    ax_bar.spines[['top', 'right']].set_visible(False)
    ax_bar.tick_params(labelbottom=False, labelsize=8)

    yrow = {p: i for i, p in enumerate(rows)}
    for j, c in enumerate(cols):
        present = members(c)
        ax_mat.scatter([j] * len(rows), range(len(rows)),
                       c=[DARK if p in present else GREY for p in rows], s=80, zorder=2)
        idx = sorted(yrow[p] for p in present)
        if len(idx) > 1:
            ax_mat.plot([j, j], [idx[0], idx[-1]], color=DARK, lw=2, zorder=1)
    ax_mat.set_yticks(range(len(rows)))
    ax_mat.set_yticklabels([NAMES[p] for p in rows], fontsize=9)
    ax_mat.set_ylim(-0.6, len(rows) - 0.4)
    ax_mat.set_xlim(-0.6, n - 0.4)
    ax_mat.tick_params(labelbottom=False, length=0)
    ax_mat.spines[['top', 'right', 'bottom', 'left']].set_visible(False)

    ax_set.barh(range(len(rows)), [marg[p] * 100 for p in rows], color='#9aa0a6', height=0.55)
    for i, p in enumerate(rows):
        ax_set.text(marg[p] * 100 + 3, i, f'{marg[p]:.0%}', va='center', ha='left',
                    fontsize=7.5, color=DARK)
    ax_set.invert_xaxis()
    ax_set.set_xlabel('carriage (%)', fontsize=8)
    ax_set.tick_params(labelleft=False, length=0, labelsize=7)
    ax_set.spines[['top', 'right', 'left']].set_visible(False)
    ax_set.set_xlim(max(marg.values()) * 100 * 1.35, 0)

    fig.text(0.5, 0.02, f'Vaginal-discharge prevalence {vds_prev:.0%} of women. '
             'Bars: share of VDS women in each mutually-exclusive infection set; left: carriage of each pathogen.',
             ha='center', fontsize=7.5, color='#666666')
    p = FIGS / 'archive' / 'fig_vds_upset.png'
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200, bbox_inches='tight', pad_inches=0.06)
    print('wrote', p)


def burden(vds_prev, marg, combo):
    fig, (axb, axp) = pl.subplots(1, 2, figsize=(9.7, 5),
                                  gridspec_kw={'width_ratios': [1, 1.7]})

    by_n = {k: 0.0 for k in (1, 2, 3, 4)}
    for c, v in combo.items():
        by_n[len(members(c))] += v
    shades = {1: '#cfe0f3', 2: '#8bbbe6', 3: BLUE, 4: '#2f6db5'}
    labels = {1: 'single pathogen', 2: 'two', 3: 'three', 4: 'four'}
    bottom = 0
    for k in (1, 2, 3, 4):
        h = by_n[k] * 100
        axb.bar(0, h, bottom=bottom * 100, color=shades[k], width=0.6)
        mid = (bottom + by_n[k] / 2) * 100
        if h > 6:
            axb.text(0, mid, f'{labels[k]}\n{h:.0f}%', ha='center', va='center',
                     fontsize=9, color='white' if k >= 3 else DARK)
        else:
            axb.annotate(f'{labels[k]} ({h:.0f}%)', xy=(0.3, mid), xytext=(0.45, mid),
                         va='center', fontsize=8.5, color=DARK,
                         arrowprops=dict(arrowstyle='-', color='#999999', lw=0.6))
        bottom += by_n[k]
    multi = sum(by_n[k] for k in (2, 3, 4))
    axb.set_xticks([]); axb.set_xlim(-0.7, 0.9); axb.set_ylim(0, 100)
    axb.set_ylabel('% of VDS women', fontsize=9.5)
    axb.set_title(f'{multi:.0%} carry >1 pathogen', fontsize=11, color=BLUE, pad=8)
    axb.spines[['top', 'right']].set_visible(False)

    rows = sorted(PATHS, key=lambda p: marg[p])
    y = np.arange(len(rows))
    alone = np.array([combo[f'{p}_only'] * 100 for p in rows])
    withoth = np.array([marg[p] * 100 for p in rows]) - alone
    axp.barh(y, alone, color=BLUE, height=0.6, label='sole pathogen')
    axp.barh(y, withoth, left=alone, color='#f0b429', height=0.6, label='with other pathogens')
    for i, p in enumerate(rows):
        axp.text(marg[p] * 100 + 1.5, i, f'{marg[p]:.0%}', va='center', fontsize=8.5, color=DARK)
    axp.set_yticks(y); axp.set_yticklabels([NAMES[p] for p in rows], fontsize=10)
    axp.set_xlabel('% of VDS women carrying pathogen', fontsize=9.5)
    axp.set_title('Each pathogen: alone vs co-infected', fontsize=11, pad=8)
    axp.set_xlim(0, max(marg.values()) * 100 * 1.12)
    axp.legend(fontsize=8, frameon=False, loc='lower right')
    axp.spines[['top', 'right']].set_visible(False)

    fig.text(0.5, 0.02, f'Single calibrated draw, women 15-49, syndromic arm. VDS prevalence {vds_prev:.0%}.',
             ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.985, top=0.92, bottom=0.12, wspace=0.25)
    p = FIGS / 'archive' / 'fig_vds_burden.png'
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200)
    print('wrote', p)


def cooccur(vds_prev, marg, combo):
    n = len(PATHS)
    M = np.zeros((n, n))
    for i, a in enumerate(PATHS):
        for j, b in enumerate(PATHS):
            M[i, j] = marg[a] if i == j else sum(
                v for c, v in combo.items() if a in members(c) and b in members(c))

    fig, ax = pl.subplots(figsize=(5.2, 4.8))
    im = ax.imshow(M * 100, cmap='Blues', vmin=0, vmax=marg['bv'] * 100)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([NAMES[p] for p in PATHS]); ax.set_yticklabels([NAMES[p] for p in PATHS])
    for i in range(n):
        for j in range(n):
            v = M[i, j] * 100
            ax.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=11,
                    color='white' if v > marg['bv'] * 100 * 0.55 else DARK,
                    fontweight='bold' if i == j else 'normal')
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label('% of VDS women', fontsize=9)
    fig.text(0.5, 0.03, 'Among VDS women: diagonal = carriage of each pathogen; '
             'off-diagonal = both present.', ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.10, right=0.99, top=0.99, bottom=0.12)
    p = FIGS / 'archive' / 'fig_vds_cooccur.png'
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200, bbox_inches='tight', pad_inches=0.06)
    print('wrote', p)


def main():
    set_font(11)
    data = load()
    upset(*data)
    burden(*data)
    cooccur(*data)


if __name__ == '__main__':
    main()
