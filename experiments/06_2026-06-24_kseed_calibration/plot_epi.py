"""Exp 06 epi overview from K=5-averaged calibration outputs.

3x5 panels (top: prevalence TS by sex, middle: new-infections TS, bottom:
age × sex prevalence at SNAP_YEAR), top-N draws by GoF (default 30,
override with TOP_N env var; TOP_N=0 plots all draws).

  conda run -n starsim python experiments/06_2026-06-24_kseed_calibration/plot_epi.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / 'outputs'
FIG_DIR = HERE
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

TOP_N = int(os.environ.get('TOP_N', 30))

DISEASES = ['ng', 'ct', 'tv', 'syph', 'hiv']
DNAME = {'ng': 'Gonorrhoea', 'ct': 'Chlamydia', 'tv': 'Trichomoniasis',
         'syph': 'Syphilis', 'hiv': 'HIV'}
AGES = ['15_20', '20_25', '25_30', '30_35', '35_50', '50_65']
AGE_LBL = ['15', '20', '25', '30', '35', '50']
SNAP_YEAR = 2027
AGE_BASE = {'ng': 'prevalence', 'ct': 'prevalence', 'tv': 'prevalence',
            'hiv': 'prevalence', 'syph': 'trep_prevalence'}

F_COLOR, M_COLOR = '#d46e9c', '#4a90d9'
F_LIGHT, M_LIGHT = '#f0a3c4', '#a3c4e8'
DATA_C = '#444444'

ZIMPHIA_HIV = {
    2016: {'15_20': (0.040, 0.025), '20_25': (0.077, 0.034), '25_30': (0.137, 0.077),
           '30_35': (0.207, 0.148), '35_50': (0.233, 0.207), '50_65': (0.130, 0.142)},
    2020: {'15_20': (0.038, 0.021), '20_25': (0.064, 0.028), '25_30': (0.106, 0.040),
           '30_35': (0.184, 0.093), '35_50': (0.295, 0.208), '50_65': (0.250, 0.251)},
}
ZIMPHIA_HIV_15_49 = {2016: 0.159, 2020: 0.148}  # ZIMPHIA 15-49 cross-sections
ZIMPHIA_SYPH_TREP = {'15_20': (0.008, 0.003), '20_25': (0.021, 0.010), '25_30': (0.024, 0.013),
                     '30_35': (0.021, 0.018), '35_50': (0.034, 0.036), '50_65': (0.086, 0.077)}


def set_font(size=9):
    if Path(FONT).exists():
        sc.fonts(add=FONT)
        sc.options(font='Libertinus Sans', fontsize=size)
    else:
        sc.options(fontsize=size)


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


def ni_data(d):
    """Whole-pop new-infection counts per year. Syph has no data overlay."""
    if d in ('ng', 'ct', 'tv'):
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
        return s.time.values, s[f'{d}_new_infections'].values / 1e3
    if d == 'hiv':
        s = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')
        return s.time.values, s.hiv_new_infections.values / 1e3
    return None, None


def main():
    set_font(9)
    pdm = pd.read_csv(OUT / 'per_draw_means.csv')
    if TOP_N > 0:
        kept = pdm.sort_values('retention_rank').head(TOP_N)
        label = f'top-{TOP_N} by GoF'
    else:
        kept = pdm
        label = f'all {len(pdm)}'
    kept_ids = set(int(x) for x in kept.draw_idx)
    print(f'plotting {len(kept_ids)} draws ({label}); worst GoF in set: {kept.gof.max():.2f}')

    ts = pd.read_parquet(OUT / 'timeseries.parquet')
    ts = ts[ts.draw_idx.isin(kept_ids)]
    sn = pd.read_parquet(OUT / 'snapshots.parquet').query('year == @SNAP_YEAR')
    sn = sn[sn.draw_idx.isin(kept_ids)]

    fig, axes = pl.subplots(3, 5, figsize=(9.7, 7.2))

    # --- top row: prevalence TS by sex (median + range) + data ---
    for ax, d in zip(axes[0], DISEASES):
        for sex, col in [('f', F_COLOR), ('m', M_COLOR)]:
            s = ts[(ts.disease == d) & (ts.result_name == f'prevalence_{sex}')]
            g = s.groupby('year').value
            med = g.median(); lo = g.quantile(0.25); hi = g.quantile(0.75)
            yr = med.index.values
            ax.fill_between(yr, lo.values * 100, hi.values * 100, color=col, alpha=0.15, lw=0)
            ax.plot(yr, med.values * 100, color=col, lw=1.5,
                    label='female' if sex == 'f' else 'male')
        if d == 'hiv':
            s49 = ts[(ts.disease == 'hiv') & (ts.result_name == 'prevalence_15_49')]
            g = s49.groupby('year').value
            med = g.median(); yr = med.index.values
            ax.plot(yr, med.values * 100, color=DATA_C, lw=1.2, ls='--', label='15-49')
            zy = list(ZIMPHIA_HIV_15_49.keys())
            zv = [ZIMPHIA_HIV_15_49[y] * 100 for y in zy]
            ax.scatter(zy, zv, s=15, color=DATA_C, marker='D', zorder=5,
                       edgecolor='white', linewidth=0.3, label='ZIMPHIA 15-49')
        else:
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

    # --- middle row: new-infections TS (model whole-pop count) + data ---
    for ax, d in zip(axes[1], DISEASES):
        s = ts[(ts.disease == d) & (ts.result_name == 'new_infections')]
        g = s.groupby('year').value
        med = g.median() / 1e3; lo = g.quantile(0.25) / 1e3; hi = g.quantile(0.75) / 1e3
        yr = med.index.values
        ax.fill_between(yr, lo.values, hi.values, color=DATA_C, alpha=0.15, lw=0)
        ax.plot(yr, med.values, color=DATA_C, lw=1.5, label='model')
        xy = ni_data(d)
        if xy[0] is not None:
            ax.scatter(xy[0], xy[1], s=13, color=DATA_C, marker='D', zorder=5,
                       edgecolor='white', linewidth=0.3, label='data')
        ax.set_xlim(1990, 2040); ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        if d == 'ng':
            ax.set_ylabel('new infections (thousands/yr)', fontsize=8.5)
    axes[1, 4].legend(fontsize=6.3, frameon=False, loc='upper right')

    # --- bottom row: prevalence by age + sex (bars, median + range) + data ---
    x = np.arange(len(AGES)); w = 0.38
    for ax, d in zip(axes[2], DISEASES):
        base = AGE_BASE[d]
        ad = sn[(sn.disease == d) & (sn.base == base)]
        for sex, off, col in [('f', -w / 2, F_COLOR), ('m', w / 2, M_COLOR)]:
            med, lo, hi = [], [], []
            for ab in AGES:
                g = ad[(ad.sex == sex) & (ad.age == ab)].value
                med.append(g.median() * 100 if len(g) else np.nan)
                lo.append(g.quantile(0.25) * 100 if len(g) else np.nan)
                hi.append(g.quantile(0.75) * 100 if len(g) else np.nan)
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

    fig.text(0.5, 0.012,
             f'Exp 06 K=5 calibration, {label} ({len(kept_ids)} draws): line/bar = median, band/whisker = 25-75 IQR across draws. '
             'Diamonds = data (programme surveillance, ZIMPHIA). HIV/NG/CT/TV new-inf data = whole-pop counts; '
             f'syphilis has no new-inf data overlay. HIV age panel overlays ZIMPHIA 2016 + 2020; '
             f'syph age is treponemal. Age panels at {SNAP_YEAR}.',
             ha='center', fontsize=6.5, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.995, top=0.95, bottom=0.08, wspace=0.32, hspace=0.36)
    suffix = f'top{TOP_N}' if TOP_N > 0 else 'all'
    p = FIG_DIR / f'fig_epi_overview_{suffix}.png'
    fig.savefig(p, dpi=200)
    print(f'wrote {p}')


if __name__ == '__main__':
    main()
