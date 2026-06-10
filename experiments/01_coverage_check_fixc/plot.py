"""
Coverage plots: ensemble (5-95%) bands vs surveillance data.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
REPO = HERE.parents[1]
DATA = REPO / 'data'
TSQ  = HERE / 'outputs' / 'ensemble_ts_quantiles.parquet'
FIG  = HERE / 'figures'
FIG.mkdir(exist_ok=True)

YEAR_LO, YEAR_HI = 1990, 2040

ZIMPHIA_NATIONAL_TREP_15_64 = 0.027
ZIMPHIA_NATIONAL_NONTREP_15_64 = 0.008
ZIMPHIA_HIV_15_49 = {2016: 0.159, 2020: 0.148}
FSW_BAND = (0.20, 0.40)

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.25,
    'figure.dpi': 120,
})

COL_MODEL = '#1f77b4'
COL_ACCENT = '#2ca02c'
COL_DATA = '#222222'


def get_series(ts, disease, result_name):
    sub = ts[(ts['disease'] == disease) & (ts['result_name'] == result_name)]
    if len(sub) == 0:
        return None
    return sub.sort_values('year')


def band(ax, s, *, color, mult=1.0, label='Model 5-95%'):
    if s is None:
        return
    x = s['year'].values
    lo = s['ci95_lo'].values * mult
    hi = s['ci95_hi'].values * mult
    med = s['median'].values * mult
    ax.fill_between(x, lo, hi, color=color, alpha=0.22, linewidth=0, label=label)
    ax.plot(x, med, color=color, lw=1.8, label='Median')
    ax.set_xlim(YEAR_LO, YEAR_HI)


def main():
    ts = pd.read_parquet(TSQ)
    hiv_data = pd.read_csv(DATA / 'zimbabwe_hiv_calib.csv')
    sti_data = pd.read_csv(DATA / 'zimbabwe_sti_data.csv')

    # ----- Syphilis ------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))

    ax = axes[0, 0]
    band(ax, get_series(ts, 'syph', 'trep_prevalence_15_64'),
         color=COL_MODEL, mult=100)
    ax.scatter([2016], [ZIMPHIA_NATIONAL_TREP_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1,
               label='ZIMPHIA 2.7%')
    ax.set_ylabel('Treponemal+ (%)')
    ax.set_title('A. Treponemal prev, 15–64')
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    ax.set_ylim(bottom=0)

    ax = axes[0, 1]
    band(ax, get_series(ts, 'syph', 'nontrep_prevalence_15_64'),
         color=COL_MODEL, mult=100)
    ax.scatter([2016], [ZIMPHIA_NATIONAL_NONTREP_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1,
               label='ZIMPHIA 0.8%')
    ax.set_ylabel('Non-treponemal+ (%)')
    ax.set_title('B. Non-trep prev, 15–64')
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    ax.set_ylim(bottom=0)

    ax = axes[1, 0]
    band(ax, get_series(ts, 'syph', 'prevalence_sw'),
         color=COL_MODEL, mult=100)
    ax.axhspan(FSW_BAND[0] * 100, FSW_BAND[1] * 100,
               color=COL_DATA, alpha=0.12, label='FSW target 20–40%')
    ax.set_ylabel('Prevalence (%)')
    ax.set_title('C. FSW syph prev')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    ax = axes[1, 1]
    band(ax, get_series(ts, 'syph', 'new_infections'),
         color=COL_MODEL, mult=1e-3)
    ax.set_ylabel('New inf (thousands/yr)')
    ax.set_title('D. Syph annual incidence')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    for ax in axes.flat:
        ax.set_xlabel('Year')
    fig.suptitle('Coverage check (Fix C, 50 prior draws): Syphilis',
                 fontsize=13, y=1.00)
    fig.tight_layout()
    out = FIG / 'fig1_syph_coverage.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    # ----- HIV -----------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    band(ax, get_series(ts, 'hiv', 'prevalence'),
         color=COL_MODEL, mult=100, label='Model (whole pop) 5-95%')
    s_1549 = get_series(ts, 'hiv', 'prevalence_15_49')
    if s_1549 is not None:
        x = s_1549['year'].values
        lo = s_1549['ci95_lo'].values * 100
        hi = s_1549['ci95_hi'].values * 100
        med = s_1549['median'].values * 100
        ax.fill_between(x, lo, hi, color=COL_ACCENT, alpha=0.18, linewidth=0,
                        label='Model (15-49) 5-95%')
        ax.plot(x, med, color=COL_ACCENT, lw=1.8)
    ax.scatter(hiv_data['time'], hiv_data['hiv_prevalence'] * 100,
               color=COL_DATA, marker='o', s=25, zorder=10,
               edgecolor='white', linewidth=0.6, label='UNAIDS whole-pop')
    ax.scatter(list(ZIMPHIA_HIV_15_49.keys()),
               [v * 100 for v in ZIMPHIA_HIV_15_49.values()],
               color=COL_ACCENT, marker='D', s=60, zorder=10,
               edgecolor='white', linewidth=1, label='ZIMPHIA (15-49)')
    ax.set_ylabel('HIV prev (%)')
    ax.set_xlabel('Year')
    ax.set_title('HIV prevalence')
    ax.legend(fontsize=8, frameon=False, loc='upper left')
    ax.set_ylim(bottom=0)

    ax = axes[1]
    band(ax, get_series(ts, 'hiv', 'new_infections'),
         color=COL_MODEL, mult=1e-3)
    ax.scatter(hiv_data['time'], hiv_data['hiv_new_infections'] * 1e-3,
               color=COL_DATA, marker='o', s=25, zorder=10,
               edgecolor='white', linewidth=0.6, label='UNAIDS')
    ax.set_ylabel('New HIV inf (thousands/yr)')
    ax.set_xlabel('Year')
    ax.set_title('HIV incidence')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    fig.suptitle('Coverage check (Fix C, 50 prior draws): HIV',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    out = FIG / 'fig2_hiv_coverage.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    # ----- Other STIs ----------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    diseases = [('ng', 'Gonorrhoea (NG)', 'prevalence', 'ng_prevalence'),
                ('ct', 'Chlamydia (CT, F 25–29)', 'prevalence_f_25_30',
                 'ct_prevalence_f_25_30'),
                ('tv', 'Trichomoniasis (TV)', 'prevalence', 'tv_prevalence')]
    for ax, (dname, dlabel, model_col, data_col) in zip(axes, diseases):
        band(ax, get_series(ts, dname, model_col),
             color=COL_MODEL, mult=100)
        if data_col in sti_data.columns:
            ax.scatter(sti_data['time'], sti_data[data_col] * 100,
                       color=COL_DATA, marker='o', s=25, zorder=10,
                       edgecolor='white', linewidth=0.6,
                       label='Surveillance')
        ax.set_ylabel('Prev (%)')
        ax.set_xlabel('Year')
        ax.set_title(dlabel)
        ax.legend(fontsize=9, frameon=False, loc='upper right')
        ax.set_ylim(bottom=0)

    fig.suptitle('Coverage check (Fix C, 50 prior draws): NG/CT/TV',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    out = FIG / 'fig3_sti_coverage.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    print(f'\nDone. {len(list(FIG.glob("*.png")))} figures in figures/')


if __name__ == '__main__':
    main()
