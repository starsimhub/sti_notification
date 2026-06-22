"""
Indicative scenario figures from exp 08 results.jsonl.

Per-cell ensemble summary (median + IQR across draws/seeds) for headline
endpoints, in the syph_dx_zim house style. Run once results.jsonl exists:

    conda run -n starsim python experiments/08_pn_bp_scenarios/figures.py

Results are INDICATIVE: the ensemble predates the BV-in-VDS edit (not yet
recalibrated). Labelled as such on the figure.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

HERE = Path(__file__).resolve().parent
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'
RESULTS = HERE / 'outputs' / 'results.jsonl'

CELL_ORDER = ['SOC', 'POC_pn_baseline', 'POC_pn_low', 'POC_pn_moderate',
              'POC_pn_high', 'POC_pn_maximum', 'POC_bp_low', 'POC_bp_moderate',
              'POC_bp_high', 'POC_bp_maximum']
CELL_LABELS = ['SOC', 'POC\nbaseline', 'PN\nlow', 'PN\nmod', 'PN\nhigh',
               'PN\nmax', 'BP\nlow', 'BP\nmod', 'BP\nhigh', 'BP\nmax']

PANELS = [
    ('ct_prev_end',         'Chlamydia prevalence, 2040',            1),
    ('ct_new_inf',          'Chlamydia new infections, 2027-40',     1e-6),
    ('_unnecessary',        'Unnecessary treatments, 2027-40 (M)',   1e-6),
    ('syph_new_congenital', 'Congenital syphilis, 2027-40 (K)',      1e-3),
]


def set_font(size=None):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def load():
    rows = [json.loads(l) for l in RESULTS.read_text().splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    df = df[df.get('status', 'ok') == 'ok'].copy()
    unn = [c for c in ['ng_new_treated_unnecessary', 'ct_new_treated_unnecessary',
                       'tv_new_treated_unnecessary', 'syph_new_treated_unnecessary']
           if c in df.columns]
    df['_unnecessary'] = df[unn].sum(axis=1) if unn else np.nan
    return df


def summarise(df):
    g = df.groupby('cell')
    out = {}
    for col, _, _ in PANELS:
        if col not in df.columns:
            continue
        out[col] = g[col].agg(median='median',
                              lo=lambda s: np.nanpercentile(s, 25),
                              hi=lambda s: np.nanpercentile(s, 75))
    return out


def main():
    set_font(size=13)
    df = load()
    ncells_present = [c for c in CELL_ORDER if c in set(df.cell)]
    summ = summarise(df)
    ndraws = df.draw.nunique()

    fig, axes = pl.subplots(2, 2, figsize=(11, 7))
    for ax, (col, title, scale) in zip(axes.flat, PANELS):
        if col not in summ:
            ax.set_visible(False)
            continue
        s = summ[col].reindex(ncells_present)
        x = np.arange(len(ncells_present))
        med = s['median'].values * scale
        lo = (s['median'] - s['lo']).values * scale
        hi = (s['hi'] - s['median']).values * scale
        colors = ['#888888' if c == 'SOC' else ('#4a90d9' if 'pn' in c or c == 'POC_pn_baseline'
                  else '#4daf4a') for c in ncells_present]
        ax.errorbar(x, med, yerr=[np.abs(lo), np.abs(hi)], fmt='none',
                    ecolor='#bbbbbb', capsize=3, zorder=1)
        ax.scatter(x, med, c=colors, s=45, zorder=2)
        ax.set_xticks(x)
        ax.set_xticklabels([CELL_LABELS[CELL_ORDER.index(c)] for c in ncells_present],
                           fontsize=9)
        ax.set_title(title, fontsize=12)
        ax.margins(y=0.15)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.text(0.5, 0.005,
             f'Median and IQR across {ndraws} draws. INDICATIVE: ensemble predates '
             'the BV-in-VDS edit (not yet recalibrated). Grey SOC, blue PN ladder, green bundled prevention.',
             ha='center', fontsize=9, color='#888888')
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    out = HERE / 'figures'
    out.mkdir(exist_ok=True)
    p = out / 'fig_scenarios_indicative.png'
    fig.savefig(p, dpi=200, bbox_inches='tight')
    print(f'cells: {ncells_present}')
    print(f'draws: {ndraws}')
    print(f'Saved {p}')
    # also dump a tidy summary table
    tab = pd.concat({k: v['median'] for k, v in summ.items()}, axis=1)
    tab.to_csv(HERE / 'outputs' / 'cell_summary_median.csv')
    print(tab.round(3))


if __name__ == '__main__':
    main()
