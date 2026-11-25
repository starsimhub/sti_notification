"""False-positive harms analysis for the reframed manuscript.

Reads results/scenarios.kavg.csv (K-averaged scalars per (cell, draw)) from
the exp 07 factorial + specificity sweep and writes:

  results/fp_cells.csv        per-cell median [IQR] of the headline metrics
  results/fp_spec_sweep.csv   specificity sweep table (manuscript Table 3)
  results/shapley.csv         Shapley decomposition of infections averted
                              across care-seeking / PN / condom counselling
  figures/fig_fp_mechanism.png
      A: false-positive share of NG/CT index cases vs NG/CT prevalence among
         women presenting for testing, one point per (cell, draw), with the
         analytic curve 1 - PPV for each specificity.
      B: false-positive share by intensity of the combined levers, per spec.
  figures/fig_harm_benefit.png
      Unnecessary partner notifications per infection averted, across the
      factorial.

Definitions (used verbatim in the manuscript):
  * Index case: a person whose NG or CT treatment fired on a timestep
    (metronidazole-only indices are excluded because metronidazole treats
    BV as well as TV, so "no STI" is not defined for them).
  * False-positive index: an index case who had neither NG nor CT at the
    moment of treatment (tx outcome tag "unnecessary" for every NG/CT
    treatment received and "successful/unsuccessful" for none).
  * Unnecessary notification: a partner notified by a false-positive index.
    Counted as pn_new_notified x false-positive share (female index flow),
    since the PN module does not tag partners by the index's status.
  * Presenter prevalence: NG-or-CT prevalence among women presenting with
    symptoms (care channel), from analyzers.PresenterEtiology.

Run (repo root):  conda run -n starsim python analysis/fp_harms.py
"""
from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
RES = REPO / 'results'
FIG = REPO / 'figures'

import sys
sys.path.insert(0, str(REPO))
from scenarios import CARE_LEVELS, PN_LEVELS, CC_LEVELS, BASE_SPEC, SPEC_SWEEP  # noqa

DIS = ('ng', 'ct', 'tv')
SENS = 0.95


def load():
    d = pd.read_csv(RES / 'scenarios.kavg.csv')
    d['new_inf'] = d[[f'{x}_new_inf' for x in DIS]].sum(axis=1)
    d['unnec_tx'] = d[[f'{x}_new_treated_unnecessary' for x in DIS]].sum(axis=1)
    d['fp_share_f'] = d.pn_new_index_no_sti_f / d.pn_new_index_total_f
    d['fp_share_m'] = d.pn_new_index_no_sti_m / d.pn_new_index_total_m
    d['fp_share'] = d.pn_new_index_no_sti / d.pn_new_index_total
    # Partners notified by female indices are (overwhelmingly) male partners.
    d['unnec_notified'] = d.pn_new_notified_m * d.fp_share_f + d.pn_new_notified_f * d.fp_share_m
    for x in ('ng', 'ct'):
        s, u = d[f'{x}_new_treated_success_f'], d[f'{x}_new_treated_unnecessary_f']
        d[f'{x}_ppv_f'] = s / (s + u)
    if 'pres_n_care_f' in d:
        d['pres_prev_ngct_f'] = d.pres_ngct_care_f / d.pres_n_care_f
        d['pres_prev_any_f'] = d.pres_any_care_f / d.pres_n_care_f
    soc = d[d.cell == 'SOC'].set_index('draw')
    for col in ('new_inf', 'unnec_tx', 'unnec_notified'):
        d[f'{col}_vs_soc'] = d[col].values - soc.loc[d.draw, col].values
    d['inf_averted'] = -d['new_inf_vs_soc']
    d['pct_inf_averted'] = d['inf_averted'] / soc.loc[d.draw, 'new_inf'].values
    d['unnec_notified_per_inf_averted'] = d['unnec_notified'] / d['inf_averted'].where(d['inf_averted'] > 0)
    return d


def q(s):
    return f'{s.median():.3g} [{s.quantile(.25):.3g}–{s.quantile(.75):.3g}]'


def summarise(d):
    cols = ['pct_inf_averted', 'fp_share_f', 'unnec_tx', 'unnec_notified',
            'ng_ppv_f', 'ct_ppv_f', 'unnec_notified_per_inf_averted']
    if 'pres_prev_ngct_f' in d:
        cols.append('pres_prev_ngct_f')
    g = d.groupby(['cell', 'care', 'pn', 'bp', 'spec'], dropna=False)
    med = g[cols].median().add_suffix('_med')
    lo = g[cols].quantile(.25).add_suffix('_p25')
    hi = g[cols].quantile(.75).add_suffix('_p75')
    out = pd.concat([med, lo, hi], axis=1).reset_index()
    out.to_csv(RES / 'fp_cells.csv', index=False)
    return out


def spec_table(d):
    sw = d[d.poc].copy()
    key = sw[['care', 'pn', 'bp']].apply(tuple, axis=1)
    from scenarios import SPEC_SWEEP_CELLS
    sw = sw[key.isin(SPEC_SWEEP_CELLS)]
    rows = []
    for (c, p, b, s), g in sw.groupby(['care', 'pn', 'bp', 'spec']):
        rows.append(dict(care=c, pn=p, cc=b, spec=s,
                         pct_inf_averted=q(g.pct_inf_averted),
                         fp_share_f=q(g.fp_share_f),
                         unnec_notified_per_yr=q(g.unnec_notified / 14),
                         pres_prev_ngct_f=q(g.pres_prev_ngct_f) if 'pres_prev_ngct_f' in g else ''))
    t = pd.DataFrame(rows)
    t.to_csv(RES / 'fp_spec_sweep.csv', index=False)
    return t


def shapley(d, metric='inf_averted'):
    """Exact Shapley values over the three levers at a given intensity.

    For each draw and each target intensity profile (all levers at level L),
    a lever's contribution is averaged over the 3! orderings of switching
    levers from baseline to L. Answers 'does the layering order matter?'
    (co-author comment, L. Newman).
    """
    base = {'care': 'baseline', 'pn': 'baseline', 'bp': 'none'}
    poc = d[d.poc & (d.spec == BASE_SPEC)].set_index(['care', 'pn', 'bp', 'draw'])[metric]
    rows = []
    for lvl_idx in (1, 2, 3):
        target = {'care': CARE_LEVELS[lvl_idx], 'pn': PN_LEVELS[lvl_idx], 'bp': CC_LEVELS[lvl_idx]}
        for draw in d.draw.unique():
            def v(active):
                k = tuple(target[f] if f in active else base[f] for f in ('care', 'pn', 'bp'))
                return poc.get(k + (draw,), np.nan)
            phi = {f: 0.0 for f in base}
            for order in itertools.permutations(base):
                active = set()
                for f in order:
                    before = v(active)
                    active.add(f)
                    phi[f] += (v(active) - before) / math.factorial(3)
            total = v(set(base)) - v(set())
            rows.append(dict(level=CARE_LEVELS[lvl_idx], draw=draw, total=total,
                             poc_alone=v(set()), **{f'phi_{f}': phi[f] for f in base}))
    s = pd.DataFrame(rows)
    s.to_csv(RES / 'shapley.csv', index=False)
    return s


def analytic_fp_share(prev, spec, sens=SENS, n_tests=2):
    """1 - PPV of 'positive for NG or CT' among women with NG/CT prevalence
    `prev` (treating the two as a single compound test)."""
    fp_neg = 1 - spec ** n_tests
    tp = prev * (sens + (1 - sens) * (1 - spec))
    return (1 - prev) * fp_neg / ((1 - prev) * fp_neg + tp)


def fig_mechanism(d):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ax = axes[0]
    xs = np.linspace(0.01, 0.5, 200)
    cmap = plt.get_cmap('viridis')
    specs = sorted(SPEC_SWEEP)
    for i, s in enumerate(specs):
        col = cmap(i / max(1, len(specs) - 1))
        ax.plot(xs, analytic_fp_share(xs, s), color=col, lw=1.5, label=f'Specificity {s:.1%}')
        if 'pres_prev_ngct_f' in d:
            sub = d[d.poc & (d.spec == s)]
            ax.scatter(sub.pres_prev_ngct_f, sub.fp_share_f, s=8, color=col, alpha=.5)
    ax.set_xlabel('NG/CT prevalence among women presenting for testing')
    ax.set_ylabel('False-positive share of NG/CT index cases (women)')
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title('A. False-positive share rises as presenter prevalence falls', fontsize=10, loc='left')

    ax = axes[1]
    combos = [('baseline', 'baseline', 'none', 'POC alone'),
              ('moderate', 'moderate', 'moderate', 'All moderate'),
              ('high', 'high', 'high', 'All high')]
    width = 0.8 / len(specs)
    for i, s in enumerate(specs):
        meds, los, his = [], [], []
        for c, p, b, _ in combos:
            g = d[(d.care == c) & (d.pn == p) & (d.bp == b) & (d.spec == s)].fp_share_f
            meds.append(g.median()); los.append(g.median() - g.quantile(.25)); his.append(g.quantile(.75) - g.median())
        x = np.arange(len(combos)) + (i - (len(specs) - 1) / 2) * width
        ax.bar(x, meds, width, yerr=[los, his], color=cmap(i / max(1, len(specs) - 1)),
               label=f'{s:.1%}', capsize=2)
    socv = d[d.cell == 'SOC'].fp_share_f.median()
    ax.axhline(socv, color='grey', ls='--', lw=1)
    ax.text(len(combos) - 0.5, socv, ' SOC', va='bottom', ha='right', color='grey', fontsize=8)
    ax.set_xticks(np.arange(len(combos)))
    ax.set_xticklabels([c[3] for c in combos])
    ax.set_ylabel('False-positive share of NG/CT index cases (women)')
    ax.set_title('B. By intervention intensity and POC specificity', fontsize=10, loc='left')
    ax.legend(title='Specificity', frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / 'fig_fp_mechanism.png', dpi=200)
    plt.close(fig)


def fig_harm_benefit(d):
    sub = d[d.poc & (d.spec == BASE_SPEC)]
    g = sub.groupby(['care', 'pn', 'bp']).agg(
        inf=('pct_inf_averted', 'median'),
        ratio=('unnec_notified_per_inf_averted', 'median')).reset_index()
    fig, ax = plt.subplots(figsize=(6, 4.5))
    sc_ = ax.scatter(100 * g.inf, g.ratio,
                     c=g.pn.map({k: i for i, k in enumerate(PN_LEVELS)}), cmap='magma', s=30)
    ax.set_xlabel('Infections averted vs SOC, 2027–2040 (%)')
    ax.set_ylabel('Unnecessary notifications per infection averted')
    cb = fig.colorbar(sc_, ax=ax, ticks=range(len(PN_LEVELS)))
    cb.ax.set_yticklabels(PN_LEVELS)
    cb.set_label('Partner notification intensity')
    fig.tight_layout()
    fig.savefig(FIG / 'fig_harm_benefit.png', dpi=200)
    plt.close(fig)


def main():
    d = load()
    summarise(d)
    print(spec_table(d).to_string(index=False))
    s = shapley(d)
    print(s.groupby('level')[['total', 'phi_care', 'phi_pn', 'phi_bp']].median())
    fig_mechanism(d)
    fig_harm_benefit(d)


if __name__ == '__main__':
    main()
