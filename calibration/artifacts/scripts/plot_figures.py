"""
Generate the 5 publication figures from the saved ensemble quantile
parquets. Adapted from experiments/41_pub_figures_final/plot.py.

Outputs:
  fig1_syph_timeseries.png         — syph trep+/nontrep+/FSW/incidence
  fig2_syph_stage_definitions.png  — sexually transmissible / symptomatic / primary
  fig3_syph_age_sex_2016.png       — age × sex bar chart vs ZIMPHIA diamonds
  fig4_hiv_timeseries.png          — HIV prevalence (whole-pop + 15-49) + incidence
  fig5_sti_timeseries.png          — NG / CT / TV
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

THIS       = Path(__file__).resolve()
REPO_ROOT  = THIS.parents[3]
DATA       = REPO_ROOT / 'data'

YEAR_LO, YEAR_HI = 1990, 2040
# ENSEMBLE_N / ENSEMBLE_LABEL get set in main() from --n-draws CLI arg.
ENSEMBLE_N = 200
ENSEMBLE_LABEL = f'{ENSEMBLE_N}-draw ensemble'

# ZIMPHIA 15-49 HIV prevalence (Robyn 2026-06-08)
ZIMPHIA_HIV_15_49 = {2016: 0.159, 2020: 0.148}

# ZIMPHIA 2015-16 totals by age (data/zimphia_2015_syph_table_18_4_A.md)
ZIMPHIA_AGE_TOTAL = {
    15: (0.005, 0.003),
    20: (0.015, 0.009),
    25: (0.019, 0.008),
    30: (0.020, 0.009),
    35: (0.030, 0.012),
    40: (0.040, 0.010),
    45: (0.035, 0.003),
    50: (0.063, 0.007),
    55: (0.094, 0.007),
    60: (0.090, 0.020),
}
ZIMPHIA_NATIONAL_TREP_15_64 = 0.027
ZIMPHIA_NATIONAL_ACTIVE_15_64 = 0.008

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'grid.alpha': 0.25,
    'grid.linestyle': '-',
    'grid.color': '#cccccc',
    'figure.dpi': 120,
})

COL_MODEL = '#1f77b4'
COL_DATA = '#222222'
COL_F = '#d62728'
COL_M = '#1f77b4'
COL_ACCENT = '#2ca02c'


def get_series(ts, disease, result_name):
    sub = ts[(ts['disease'] == disease) & (ts['result_name'] == result_name)]
    if len(sub) == 0:
        return None
    return sub.sort_values('year')


def plot_one_ts(ax, series, *, color=COL_MODEL, label='Model (median)',
                multiplier=1.0, fill_alpha=0.25):
    if series is None:
        ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center')
        return
    y = series['median'].values * multiplier
    lo = series['ci80_lo'].values * multiplier
    hi = series['ci80_hi'].values * multiplier
    x = series['year'].values
    ax.fill_between(x, lo, hi, color=color, alpha=fill_alpha, linewidth=0)
    ax.plot(x, y, color=color, lw=2, label=label)
    ax.set_xlim(YEAR_LO, YEAR_HI)


def add_data_points(ax, df, year_col, value_col, *, label='Zimbabwe data',
                    multiplier=1.0, color=COL_DATA, marker='o', size=35):
    if df is None or len(df) == 0:
        return
    ax.scatter(df[year_col], df[value_col] * multiplier,
               color=color, marker=marker, s=size, label=label,
               zorder=10, edgecolor='white', linewidth=0.8)


def fig_syph_timeseries(ts, fig_dir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))

    ax = axes[0, 0]
    plot_one_ts(ax, get_series(ts, 'syph', 'trep_prevalence_15_64'),
                color=COL_MODEL, multiplier=100)
    ax.axhline(ZIMPHIA_NATIONAL_TREP_15_64 * 100, color=COL_DATA,
               linestyle='--', alpha=0.7, label='ZIMPHIA 2015-16 (2.7%)')
    ax.scatter([2016], [ZIMPHIA_NATIONAL_TREP_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1)
    ax.set_ylabel('Treponemal+ prevalence (%)')
    ax.set_title('A. Treponemal prevalence, 15–64')
    ax.legend(loc='upper left', fontsize=9, frameon=False)
    ax.set_ylim(bottom=0)

    ax = axes[0, 1]
    plot_one_ts(ax, get_series(ts, 'syph', 'nontrep_prevalence_15_64'),
                color=COL_MODEL, multiplier=100)
    ax.axhline(ZIMPHIA_NATIONAL_ACTIVE_15_64 * 100, color=COL_DATA,
               linestyle='--', alpha=0.7, label='ZIMPHIA 2015-16 (0.8%)')
    ax.scatter([2016], [ZIMPHIA_NATIONAL_ACTIVE_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1)
    ax.set_ylabel('Non-treponemal+ prevalence (%)')
    ax.set_title('B. Non-treponemal prevalence, 15–64')
    ax.legend(loc='upper left', fontsize=9, frameon=False)
    ax.set_ylim(bottom=0)

    ax = axes[1, 0]
    plot_one_ts(ax, get_series(ts, 'syph', 'prevalence_sw'),
                color=COL_MODEL, multiplier=100)
    ax.set_ylabel('Syphilis prevalence (%)')
    ax.set_title('C. Prevalence in sex workers')
    ax.set_ylim(bottom=0)

    ax = axes[1, 1]
    plot_one_ts(ax, get_series(ts, 'syph', 'new_infections'),
                color=COL_MODEL, multiplier=1e-3)
    ax.set_ylabel('New infections (thousands per year)')
    ax.set_title('D. Annual incidence')
    ax.set_ylim(bottom=0)

    for ax in axes.flat:
        ax.set_xlabel('Year')

    fig.suptitle(f'Zimbabwe syphilis: {ENSEMBLE_LABEL} (median + 80% CI)',
                 fontsize=13, y=1.00)
    fig.tight_layout()
    out = fig_dir / 'fig1_syph_timeseries.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')


def fig_syph_definitions(ts, fig_dir: Path):
    fig, ax = plt.subplots(1, 1, figsize=(9, 5.5))
    defs = [
        ('sexually_transmissible_prevalence',
         'Sexually transmissible (primary + secondary + early latent)',
         COL_ACCENT),
        ('symptomatic_prevalence', 'Symptomatic (primary + secondary)', COL_F),
        ('primary_prevalence', 'Primary stage', COL_M),
    ]
    for rname, label, color in defs:
        s = get_series(ts, 'syph', rname)
        if s is None:
            continue
        y = s['median'].values * 100
        lo = s['ci80_lo'].values * 100
        hi = s['ci80_hi'].values * 100
        x = s['year'].values
        ax.fill_between(x, lo, hi, color=color, alpha=0.18, linewidth=0)
        ax.plot(x, y, color=color, lw=2, label=label)

    ax.set_xlabel('Year')
    ax.set_ylabel('Prevalence (%)')
    ax.set_title(f'Syphilis prevalence by clinical stage definition\n'
                 f'({ENSEMBLE_LABEL}: median + 80% CI)')
    ax.legend(loc='upper right', fontsize=10, frameon=False)
    ax.set_xlim(YEAR_LO, YEAR_HI)
    ax.set_ylim(bottom=0)

    fig.tight_layout()
    out = fig_dir / 'fig2_syph_stage_definitions.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')


def fig_syph_age_sex_2016(snap, fig_dir: Path):
    year = 2016
    metrics = [
        ('trep_prevalence', 'Treponemal+ (%)'),
        ('nontrep_prevalence', 'Non-treponemal+ (%)'),
        ('sexually_transmissible_prevalence', 'Sexually transmissible (%)'),
    ]
    age_bins = ['15_20', '20_25', '25_30', '30_35', '35_50', '50_65']
    age_labels = ['15–19', '20–24', '25–29', '30–34', '35–49', '50–64']

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (rname, ylabel) in zip(axes, metrics):
        sub = snap[(snap['year'] == year) & (snap['disease'] == 'syph') &
                   (snap['result_name'] == rname) &
                   (snap['age_bin'].isin(age_bins))]
        if len(sub) == 0:
            ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center')
            continue

        f_vals, f_err_lo, f_err_hi = [], [], []
        m_vals, m_err_lo, m_err_hi = [], [], []
        for ab in age_bins:
            f_row = sub[(sub['age_bin'] == ab) & (sub['sex'] == 'f')]
            m_row = sub[(sub['age_bin'] == ab) & (sub['sex'] == 'm')]
            f_vals.append(f_row['median'].iloc[0] * 100 if len(f_row) else 0)
            f_err_lo.append((f_row['median'].iloc[0] - f_row['ci80_lo'].iloc[0]) * 100
                            if len(f_row) else 0)
            f_err_hi.append((f_row['ci80_hi'].iloc[0] - f_row['median'].iloc[0]) * 100
                            if len(f_row) else 0)
            m_vals.append(m_row['median'].iloc[0] * 100 if len(m_row) else 0)
            m_err_lo.append((m_row['median'].iloc[0] - m_row['ci80_lo'].iloc[0]) * 100
                            if len(m_row) else 0)
            m_err_hi.append((m_row['ci80_hi'].iloc[0] - m_row['median'].iloc[0]) * 100
                            if len(m_row) else 0)

        x = np.arange(len(age_bins))
        w = 0.4
        ax.bar(x - w/2, f_vals, w, color=COL_F, alpha=0.85, label='Female',
               yerr=[f_err_lo, f_err_hi], capsize=3, ecolor='#333')
        ax.bar(x + w/2, m_vals, w, color=COL_M, alpha=0.85, label='Male',
               yerr=[m_err_lo, m_err_hi], capsize=3, ecolor='#333')

        if rname in ('trep_prevalence', 'nontrep_prevalence'):
            zimphia_vals = []
            for ab_lo in [15, 20, 25, 30, 35, 50]:
                if ab_lo == 35:
                    if rname == 'trep_prevalence':
                        v = np.mean([ZIMPHIA_AGE_TOTAL[a][0] for a in (35, 40, 45)])
                    else:
                        v = np.mean([ZIMPHIA_AGE_TOTAL[a][1] for a in (35, 40, 45)])
                elif ab_lo == 50:
                    if rname == 'trep_prevalence':
                        v = np.mean([ZIMPHIA_AGE_TOTAL[a][0] for a in (50, 55, 60)])
                    else:
                        v = np.mean([ZIMPHIA_AGE_TOTAL[a][1] for a in (50, 55, 60)])
                else:
                    v = ZIMPHIA_AGE_TOTAL[ab_lo][0 if rname == 'trep_prevalence' else 1]
                zimphia_vals.append(v * 100)
            ax.scatter(x, zimphia_vals, color=COL_DATA, marker='D', s=55,
                       label='ZIMPHIA 2015-16 (total)', zorder=10,
                       edgecolor='white', linewidth=1.2)

        ax.set_xticks(x)
        ax.set_xticklabels(age_labels, rotation=0)
        ax.set_xlabel('Age group')
        ax.set_ylabel(ylabel)
        ax.set_title(ylabel.replace(' (%)', ''))
        ax.legend(loc='upper left', fontsize=9, frameon=False)
        ax.set_ylim(bottom=0)

    fig.suptitle(f'Syphilis prevalence by age and sex at {year} '
                 f'({ENSEMBLE_LABEL} median + 80% CI; bars = model, '
                 'diamonds = ZIMPHIA)', y=1.02, fontsize=12)
    fig.tight_layout()
    out = fig_dir / f'fig3_syph_age_sex_{year}.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')


def fig_hiv_timeseries(ts, fig_dir: Path):
    hiv_data = pd.read_csv(DATA / 'zimbabwe_hiv_calib.csv')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    plot_one_ts(ax, get_series(ts, 'hiv', 'prevalence'),
                color=COL_MODEL, multiplier=100,
                label='Model (whole pop)', fill_alpha=0.18)
    s_1549 = get_series(ts, 'hiv', 'prevalence_15_49')
    if s_1549 is not None:
        x = s_1549['year'].values
        y = s_1549['median'].values * 100
        lo = s_1549['ci80_lo'].values * 100
        hi = s_1549['ci80_hi'].values * 100
        ax.fill_between(x, lo, hi, color=COL_ACCENT, alpha=0.18, linewidth=0)
        ax.plot(x, y, color=COL_ACCENT, lw=2, label='Model (15–49)')
    add_data_points(ax, hiv_data, 'time', 'hiv_prevalence', multiplier=100,
                    label='UNAIDS (whole pop)', color=COL_MODEL,
                    marker='o', size=30)
    ax.scatter(list(ZIMPHIA_HIV_15_49.keys()),
               [v * 100 for v in ZIMPHIA_HIV_15_49.values()],
               color=COL_ACCENT, marker='D', s=70, zorder=10,
               edgecolor='white', linewidth=1.2, label='ZIMPHIA (15–49)')
    ax.set_ylabel('HIV prevalence (%)')
    ax.set_xlabel('Year')
    ax.set_title('HIV prevalence')
    ax.legend(loc='upper left', fontsize=8, frameon=False)
    ax.set_ylim(bottom=0)

    ax = axes[1]
    plot_one_ts(ax, get_series(ts, 'hiv', 'new_infections'),
                color=COL_MODEL, multiplier=1e-3)
    add_data_points(ax, hiv_data, 'time', 'hiv_new_infections', multiplier=1e-3,
                    label='UNAIDS')
    ax.set_ylabel('New HIV infections (thousands per year)')
    ax.set_xlabel('Year')
    ax.set_title('HIV incidence')
    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.set_ylim(bottom=0)

    fig.suptitle(f'HIV calibration check ({ENSEMBLE_LABEL})',
                 y=1.02, fontsize=12)
    fig.tight_layout()
    out = fig_dir / 'fig4_hiv_timeseries.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')


def fig_sti_timeseries(ts, fig_dir: Path):
    sti_data = pd.read_csv(DATA / 'zimbabwe_sti_data.csv')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    diseases = [('ng', 'Gonorrhoea (NG)'),
                ('ct', 'Chlamydia (CT, F 25–29)'),
                ('tv', 'Trichomoniasis (TV)')]
    data_cols = {'ng': 'ng_prevalence',
                 'ct': 'ct_prevalence_f_25_30',
                 'tv': 'tv_prevalence'}
    model_results = {'ng': 'prevalence', 'ct': 'prevalence_f_25_30',
                     'tv': 'prevalence'}

    for ax, (dname, dlabel) in zip(axes, diseases):
        s = get_series(ts, dname, model_results[dname])
        plot_one_ts(ax, s, color=COL_MODEL, multiplier=100)
        if data_cols[dname] in sti_data.columns:
            add_data_points(ax, sti_data, 'time', data_cols[dname],
                            multiplier=100, label='Surveillance')
        ax.set_ylabel('Prevalence (%)')
        ax.set_xlabel('Year')
        ax.set_title(dlabel)
        ax.legend(loc='upper right', fontsize=9, frameon=False)
        ax.set_ylim(bottom=0)

    fig.suptitle(f'Other STIs: prevalence calibration ({ENSEMBLE_LABEL})',
                 y=1.02, fontsize=12)
    fig.tight_layout()
    out = fig_dir / 'fig5_sti_timeseries.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    artifacts = THIS.parents[1]
    ap.add_argument('--ts-quantiles', type=Path,
                    default=artifacts / 'ensemble_ts_quantiles.parquet')
    ap.add_argument('--snap-quantiles', type=Path,
                    default=artifacts / 'ensemble_snapshots_quantiles.parquet')
    ap.add_argument('--fig-dir', type=Path,
                    default=artifacts / 'figures',
                    help='Output directory for the 5 PNGs.')
    ap.add_argument('--n-draws', type=int, default=200,
                    help='Number of draws in the ensemble; used in figure '
                         'suptitle labels (default 200).')
    args = ap.parse_args()

    global ENSEMBLE_N, ENSEMBLE_LABEL
    ENSEMBLE_N = args.n_draws
    ENSEMBLE_LABEL = f'{ENSEMBLE_N}-draw ensemble'

    args.fig_dir.mkdir(parents=True, exist_ok=True)
    print(f'Writing figures to {args.fig_dir}/ (label: {ENSEMBLE_LABEL})')

    ts = pd.read_parquet(args.ts_quantiles)
    snap = pd.read_parquet(args.snap_quantiles)

    fig_syph_timeseries(ts, args.fig_dir)
    fig_syph_definitions(ts, args.fig_dir)
    fig_syph_age_sex_2016(snap, args.fig_dir)
    fig_hiv_timeseries(ts, args.fig_dir)
    fig_sti_timeseries(ts, args.fig_dir)

    print(f'\nDone. {len(list(args.fig_dir.glob("*.png")))} figures.')


if __name__ == '__main__':
    main()
