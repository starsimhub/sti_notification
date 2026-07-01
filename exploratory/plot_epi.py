"""Baseline epidemiology overview (SOC), 2x5, 9.7w x 5h.

Sourced entirely from the factorial pilot parquets (SOC cell, 3 draws, 1 seed):
  results/scenarios_timeseries.parquet   prevalence by sex, all years
  results/scenarios_snapshots.parquet    prevalence by age x sex (2027+ only)

Top row:    prevalence time series by sex (model median + range, + data) for
            NG, CT, TV, syphilis, HIV.
Bottom row: prevalence by age and sex (model bars at the earliest snapshot, 2027,
            + data points). HIV is layered across ZIMPHIA years (2016 + 2020);
            the others have a single data reference.

House style, no figure title.  conda run -n starsim python plot_epi.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent.parent
FIGS = REPO / 'figures'
TS = REPO / 'results' / 'scenarios_timeseries.parquet'
SNAP = REPO / 'results' / 'scenarios_snapshots.parquet'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

DISEASES = ['ng', 'ct', 'tv', 'syph', 'hiv']
DNAME = {'ng': 'Gonorrhoea', 'ct': 'Chlamydia', 'tv': 'Trichomoniasis',
         'syph': 'Syphilis', 'hiv': 'HIV'}
AGES = ['15_20', '20_25', '25_30', '30_35', '35_50', '50_65']
AGE_LBL = ['15', '20', '25', '30', '35', '50']
SNAP_YEAR = 2027
# bottom-row prevalence base per disease (syph: treponemal, to match ZIMPHIA trep)
AGE_BASE = {'ng': 'prevalence', 'ct': 'prevalence', 'tv': 'prevalence',
            'hiv': 'prevalence', 'syph': 'trep_prevalence'}

F_COLOR, M_COLOR = '#d46e9c', '#4a90d9'
F_LIGHT, M_LIGHT = '#f0a3c4', '#a3c4e8'
DATA_C = '#444444'

# ZIMPHIA HIV prevalence by age/sex (female, male) — from syph_dx_zim/plot_fig1_epi.py
ZIMPHIA_HIV = {
    2016: {'15_20': (0.040, 0.025), '20_25': (0.077, 0.034), '25_30': (0.137, 0.077),
           '30_35': (0.207, 0.148), '35_50': (0.233, 0.207), '50_65': (0.130, 0.142)},
    2020: {'15_20': (0.038, 0.021), '20_25': (0.064, 0.028), '25_30': (0.106, 0.040),
           '30_35': (0.184, 0.093), '35_50': (0.295, 0.208), '50_65': (0.250, 0.251)},
}
# ZIMPHIA treponemal (ever-exposed) syphilis by age/sex — matches model trep_prevalence
ZIMPHIA_SYPH_TREP = {'15_20': (0.008, 0.003), '20_25': (0.021, 0.010), '25_30': (0.024, 0.013),
                     '30_35': (0.021, 0.018), '35_50': (0.034, 0.036), '50_65': (0.086, 0.077)}


def set_font(size=9):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def med_range(g):
    """median, min, max over draws for a grouped value series."""
    return g.median(), g.min(), g.max()


# ---------------------------------------------------------------- data overlays
def ts_data(d):
    out = []
    if d in ('ng', 'tv'):
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
        out.append((s.time.values, s[f'{d}_prevalence'].values * 100, DATA_C, 'data'))
    elif d == 'ct':
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
        out.append((s.time.values, s['ct_prevalence_f_25_30'].values * 100, F_COLOR, 'data (F 25-30)'))
    elif d == 'syph':
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_syph_data.csv')
        for col, c in [('syph.prevalence_f', F_COLOR), ('syph.prevalence_m', M_COLOR)]:
            ss = s[['time', col]].dropna()
            out.append((ss.time.values, ss[col].values * 100, c, None))
    elif d == 'hiv':
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')
        out.append((s.time.values, s.hiv_prevalence.values * 100, DATA_C, 'data'))
    return out


# ---------------------------------------------------------------- figure
def main():
    set_font(9)
    ts = pd.read_parquet(TS).query("cell == 'SOC'")
    sn = pd.read_parquet(SNAP).query("cell == 'SOC' and year == @SNAP_YEAR")
    ndraws = ts.draw.nunique()

    fig, axes = pl.subplots(2, 5, figsize=(12.15, 5))

    # --- top row: prevalence TS by sex (median + range) + data ---
    for ax, d in zip(axes[0], DISEASES):
        for sex, col in [('f', F_COLOR), ('m', M_COLOR)]:
            s = ts[(ts.disease == d) & (ts.result_name == f'prevalence_{sex}')]
            g = s.groupby('year').value
            med, lo, hi = med_range(g)
            yr = med.index.values
            ax.fill_between(yr, lo.values * 100, hi.values * 100, color=col, alpha=0.15, lw=0)
            ax.plot(yr, med.values * 100, color=col, lw=1.5,
                    label='female' if sex == 'f' else 'male')
        for yrs, vals, c, lab in ts_data(d):
            ax.scatter(yrs, vals, s=13, color=c, marker='D', zorder=5,
                       edgecolor='white', linewidth=0.3, label=lab)
        ax.set_title(DNAME[d], fontsize=10, pad=3)
        ax.set_xlim(1990, 2040); ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        if d == 'ng':
            ax.set_ylabel('prevalence (%)', fontsize=8.5)
    axes[0, 4].legend(fontsize=6.3, frameon=False, loc='upper right')

    # --- bottom row: prevalence by age + sex (bars, median + range) + data ---
    x = np.arange(len(AGES)); w = 0.38
    for ax, d in zip(axes[1], DISEASES):
        base = AGE_BASE[d]
        ad = sn[(sn.disease == d) & (sn.result_name == base)]
        for sex, off, col in [('f', -w / 2, F_COLOR), ('m', w / 2, M_COLOR)]:
            med, lo, hi = [], [], []
            for ab in AGES:
                g = ad[(ad.sex == sex) & (ad.age_bin == ab)].value
                med.append(g.median() * 100 if len(g) else np.nan)
                lo.append(g.min() * 100 if len(g) else np.nan)
                hi.append(g.max() * 100 if len(g) else np.nan)
            med = np.array(med)
            yerr = np.vstack([med - np.array(lo), np.array(hi) - med])
            ax.bar(x + off, med, w, color=col, alpha=0.85)
            ax.errorbar(x + off, med, yerr=yerr, fmt='none', ecolor='#666666',
                        elinewidth=0.6, capsize=1.5, zorder=4)
        if d == 'hiv':
            for yr, mk, fc, mc in [(2016, 'o', F_LIGHT, M_LIGHT), (2020, 'D', F_COLOR, M_COLOR)]:
                for sex, off, c in [('f', -w / 2, fc), ('m', w / 2, mc)]:
                    yv = [ZIMPHIA_HIV[yr][ab][0 if sex == 'f' else 1] * 100 for ab in AGES]
                    ax.scatter(x + off, yv, s=12, color=c, marker=mk, zorder=5,
                               edgecolor='white', linewidth=0.3,
                               label=f'ZIMPHIA {yr}' if sex == 'f' else None)
            ax.legend(fontsize=6, frameon=False, loc='upper left')
        elif d == 'syph':
            for sex, off, c in [('f', -w / 2, F_COLOR), ('m', w / 2, M_COLOR)]:
                yv = [ZIMPHIA_SYPH_TREP[ab][0 if sex == 'f' else 1] * 100 for ab in AGES]
                ax.scatter(x + off, yv, s=12, color=c, marker='D', zorder=5,
                           edgecolor='white', linewidth=0.3)
        ax.set_xticks(x); ax.set_xticklabels(AGE_LBL, fontsize=6.5)
        ax.set_xlabel('age', fontsize=7.5); ax.set_ylim(bottom=0)
        ax.tick_params(axis='y', labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        if d == 'ng':
            ax.set_ylabel(f'prevalence (%), {SNAP_YEAR}', fontsize=8.5)

    # fig.text(0.5, 0.015,
    #          f'SOC (syndromic) model, {ndraws} calibration draws: line/bar = median, band/whisker = range. '
    #          'Diamonds = data (programme surveillance, ZIMPHIA). HIV age panel overlays ZIMPHIA 2016 + 2020; '
    #          'syphilis age is treponemal. Model age panels at 2027.',
    #          ha='center', fontsize=6.8, color='#666666')
    fig.subplots_adjust(left=0.06, right=0.995, top=0.93, bottom=0.13, wspace=0.32, hspace=0.42)
    p = FIGS / 'supplementary' / 'fig_epi_overview.png'
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
