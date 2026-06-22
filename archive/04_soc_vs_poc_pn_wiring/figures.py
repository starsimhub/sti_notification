"""Figures for the exp 04 CT partner-notification chain trace.

Reads outputs/chain_tree_{A,B}.json and outputs/arm_comparison.csv.

  fig1_ct_chain_flow_A.png  — SOC + baseline PN cohort flow
  fig1_ct_chain_flow_B.png  — POC + PN×3 cohort flow
  fig2_arm_comparison.png   — A vs B: prevalence, cohort reinfection, PN reach

Run from the repo root: python experiments/04_soc_vs_poc_pn_wiring/figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs'
FIG = HERE / 'figures'

ARM_TITLE = {'A': 'arm A — SOC + baseline PN', 'B': 'arm B — POC + PN×3'}


def _box(ax, x, y, h, w, label, color):
    ax.add_patch(FancyBboxPatch((x, y - h / 2), w, h,
                                boxstyle='round,pad=0.002,rounding_size=0.01',
                                linewidth=1.0, edgecolor='#333', facecolor=color))
    ax.text(x + w / 2, y, label, ha='center', va='center', fontsize=8.5)


def _link(ax, x0, y0, x1, y1):
    ax.plot([x0, x1], [y0, y1], color='#999', lw=1.0, zorder=0)


def draw_tree(arm):
    tree = json.loads((OUT / f'chain_tree_{arm}.json').read_text())
    n = tree['cohort']; nn = tree['not_notified']; no = tree['notified']
    H = 0.80
    def h(c):
        return max(0.012, H * c / max(n, 1))

    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    W = 0.16
    xs = [0.01, 0.27, 0.53, 0.79]

    _box(ax, xs[0], 0.5, h(n), W, f'{n}\nCT-treated\nindex cases (A)', '#cfe8ff')

    y_not, y_silent = 0.74, 0.28
    _box(ax, xs[1], y_not, h(no['total']), W, f"notified ≥1 partner\n{no['total']}", '#c9f0d2')
    _box(ax, xs[1], y_silent, h(nn['total']), W,
         f"did NOT notify\n{nn['total']}\n(no partner {nn['no_partner']}, "
         f"silent {nn['had_partner_silent']})", '#ffe0c2')
    _link(ax, xs[0] + W, 0.5, xs[1], y_not)
    _link(ax, xs[0] + W, 0.5, xs[1], y_silent)

    y_att, y_natt = 0.84, 0.60
    _box(ax, xs[2], y_att, h(no['partner_attended']), W,
         f"partner attended\n{no['partner_attended']}", '#a9e3ba')
    _box(ax, xs[2], y_natt, h(no['partner_not_attended']), W,
         f"partner did NOT attend\n{no['partner_not_attended']}", '#ffd0a0')
    _link(ax, xs[1] + W, y_not, xs[2], y_att)
    _link(ax, xs[1] + W, y_not, xs[2], y_natt)

    y_re, y_clear = 0.34, 0.14
    _box(ax, xs[2], y_re, h(nn['reinfected']), W, f"A REINFECTED\n{nn['reinfected']}", '#ff9e9e')
    _box(ax, xs[2], y_clear, h(nn['stayed_clear']), W, f"A stayed clear\n{nn['stayed_clear']}", '#d7d7d7')
    _link(ax, xs[1] + W, y_silent, xs[2], y_re)
    _link(ax, xs[1] + W, y_silent, xs[2], y_clear)

    y_cured, y_ncured = 0.90, 0.74
    _box(ax, xs[3], y_cured, h(no['attended_partner_cured']), W,
         f"partner CURED\n{no['attended_partner_cured']}", '#7fd496')
    _box(ax, xs[3], y_ncured, h(no['attended_partner_not_cured']), W,
         f"partner not cured\n{no['attended_partner_not_cured']}", '#ffd0a0')
    _link(ax, xs[2] + W, y_att, xs[3], y_cured)
    _link(ax, xs[2] + W, y_att, xs[3], y_ncured)

    y_nr, y_nc = 0.62, 0.52
    _box(ax, xs[3], y_nr, h(no['notattend_reinf_index']), W,
         f"A reinfected\n{no['notattend_reinf_index']} "
         f"(by that partner {no['notattend_reinf_by_that_partner']})", '#ff9e9e')
    _box(ax, xs[3], y_nc, h(no['notattend_clear']), W, f"clear {no['notattend_clear']}", '#d7d7d7')
    _link(ax, xs[2] + W, y_natt, xs[3], y_nr)
    _link(ax, xs[2] + W, y_natt, xs[3], y_nc)

    for x, t in zip(xs, ['index cured', 'told a partner?',
                         'partner attended? /\nindex reinfected?',
                         'partner cured? /\nindex reinfected?']):
        ax.text(x + W / 2, 0.985, t, ha='center', va='top', fontsize=9,
                fontweight='bold', color='#444')
    fig.suptitle(f'Exp 04 — CT PN chains, {ARM_TITLE[arm]} '
                 f'(draw 773, 1 seed, 12-mo follow-up)', fontsize=11, y=0.06)
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / f'fig1_ct_chain_flow_{arm}.png'
    fig.savefig(p, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {p}')


def comparison():
    comp = pd.read_csv(OUT / 'arm_comparison.csv', index_col=0)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    arms = list(comp.index)
    colors = ['#f0a868', '#7fd496']
    panels = [
        ('prev_window_mean', 'CT prevalence (2030–34 mean)', 1),
        ('cohort_reinfected', 'cohort reinfected / 100 (12 mo)', 1),
        ('pn_attending_window', 'PN partners attending (window)', 1e-6),
    ]
    for ax, (col, title, scale) in zip(axes, panels):
        vals = comp[col].values * scale
        ax.bar(arms, vals, color=colors, edgecolor='#333')
        for i, v in enumerate(vals):
            ax.text(i, v, f'{v:,.2f}' if scale != 1 else f'{v:,.3g}',
                    ha='center', va='bottom', fontsize=9)
        ax.set_title(title + (' (millions)' if scale == 1e-6 else ''), fontsize=10)
        ax.margins(y=0.15)
    fig.suptitle('Exp 04 — SOC (A) vs POC+PN×3 (B): better but modest '
                 '(draw 773, CT)', fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = FIG / 'fig2_arm_comparison.png'
    fig.savefig(p, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {p}')


def source_attribution():
    pop = pd.read_csv(OUT / 'source_breakdown_population.csv', index_col=0)
    reinf = pd.read_csv(OUT / 'source_breakdown_cohort_reinf.csv', index_col=0)
    cats = ['fsw', 'client', 'f_other', 'm_other']
    labels = ['FSW', 'client', 'regular F', 'regular M']
    colors = ['#d1495b', '#edae49', '#66a182', '#2e4057']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    for ax, df, title, ylab in (
            (ax1, pop, f'All CT transmissions by source\n(window, transactional = FSW+client)', 'share'),
            (ax2, reinf, 'Cohort reinfection sources\n(per 100 treated index)', 'count')):
        shares = df.reindex(cats).fillna(0)
        if ylab == 'share':
            shares = shares / shares.sum()
        bottom = np.zeros(len(df.columns))
        for cat, lab, col in zip(cats, labels, colors):
            vals = shares.loc[cat].values
            ax.bar(df.columns, vals, bottom=bottom, label=lab, color=col,
                   edgecolor='white')
            bottom += vals
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylab)
        ax.set_xlabel('arm')
    # transactional annotation on population panel
    pop_sh = (pop.reindex(cats).fillna(0) / pop.reindex(cats).fillna(0).sum())
    for i, arm in enumerate(pop.columns):
        tx_share = pop_sh.loc[['fsw', 'client'], arm].sum()
        ax1.text(i, 1.02, f'transactional\n{tx_share:.0%}', ha='center',
                 fontsize=8.5, color='#d1495b')
    ax2.legend(fontsize=8, loc='upper right')
    fig.suptitle('Exp 04 — CT transmission & reinfection sources (draw 773): '
                 'regular partners dominate, not sex work', fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = FIG / 'fig3_source_attribution.png'
    fig.savefig(p, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {p}')


def main():
    for arm in ('A', 'B'):
        draw_tree(arm)
    comparison()
    source_attribution()


if __name__ == '__main__':
    main()
