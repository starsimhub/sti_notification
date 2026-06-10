"""
Coverage check, sustained-only subset: filter draws where syph
sustains endemic transmission (mean new_infections 2030-2040 > 0)
and recompute the ensemble bands.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
REPO = HERE.parents[1]
DATA = REPO / 'data'
TS  = HERE / 'outputs' / 'time_series.parquet'
FIG = HERE / 'figures'
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


def compute_q(ts):
    return (ts.groupby(['disease', 'result_name', 'year'])['value']
            .agg(median='median',
                 ci80_lo=lambda s: np.quantile(s, 0.10),
                 ci80_hi=lambda s: np.quantile(s, 0.90),
                 ci95_lo=lambda s: np.quantile(s, 0.025),
                 ci95_hi=lambda s: np.quantile(s, 0.975),
                 n='count')
            .reset_index())


def get_series(q, disease, rn):
    sub = q[(q['disease'] == disease) & (q['result_name'] == rn)]
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
    ts = pd.read_parquet(TS)
    n_total = ts['draw_idx'].nunique()
    print(f'Total draws: {n_total}')

    # Sustained = mean syph new_infections 2030-2040 > 0
    ni = ts[(ts['disease'] == 'syph') & (ts['result_name'] == 'new_infections')
            & (ts['year'] >= 2030) & (ts['year'] <= 2040)]
    mean_late = ni.groupby('draw_idx')['value'].mean()
    sustained_draws = mean_late[mean_late > 0].index.tolist()
    print(f'Sustained syph (new_inf 2030-2040 mean > 0): '
          f'{len(sustained_draws)} / {n_total} = '
          f'{len(sustained_draws)/n_total*100:.1f}%')

    pd.Series(sustained_draws, name='draw_idx').to_csv(
        HERE / 'outputs' / 'sustained_draws.csv', index=False)

    ts_sus = ts[ts['draw_idx'].isin(sustained_draws)]
    q_sus = compute_q(ts_sus)
    q_sus.to_parquet(HERE / 'outputs' / 'sustained_ts_quantiles.parquet',
                     index=False)

    # ----- Syphilis ------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))

    ax = axes[0, 0]
    band(ax, get_series(q_sus, 'syph', 'trep_prevalence_15_64'),
         color=COL_MODEL, mult=100)
    ax.scatter([2016], [ZIMPHIA_NATIONAL_TREP_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1,
               label='ZIMPHIA 2.7%')
    ax.set_ylabel('Treponemal+ (%)')
    ax.set_title('A. Treponemal prev, 15–64')
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    ax.set_ylim(bottom=0)

    ax = axes[0, 1]
    band(ax, get_series(q_sus, 'syph', 'nontrep_prevalence_15_64'),
         color=COL_MODEL, mult=100)
    ax.scatter([2016], [ZIMPHIA_NATIONAL_NONTREP_15_64 * 100], color=COL_DATA,
               s=70, zorder=10, edgecolor='white', linewidth=1,
               label='ZIMPHIA 0.8%')
    ax.set_ylabel('Non-treponemal+ (%)')
    ax.set_title('B. Non-trep prev, 15–64')
    ax.legend(fontsize=9, frameon=False, loc='upper left')
    ax.set_ylim(bottom=0)

    ax = axes[1, 0]
    band(ax, get_series(q_sus, 'syph', 'prevalence_sw'),
         color=COL_MODEL, mult=100)
    ax.axhspan(FSW_BAND[0] * 100, FSW_BAND[1] * 100,
               color=COL_DATA, alpha=0.12, label='FSW target 20–40%')
    ax.set_ylabel('Prevalence (%)')
    ax.set_title('C. FSW syph prev')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    ax = axes[1, 1]
    band(ax, get_series(q_sus, 'syph', 'new_infections'),
         color=COL_MODEL, mult=1e-3)
    ax.set_ylabel('New inf (thousands/yr)')
    ax.set_title('D. Syph annual incidence')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    for ax in axes.flat:
        ax.set_xlabel('Year')
    fig.suptitle(f'Coverage check, sustained subset '
                 f'(Fix C, {len(sustained_draws)}/{n_total} draws): Syphilis',
                 fontsize=13, y=1.00)
    fig.tight_layout()
    out = FIG / 'fig1_syph_coverage_sustained.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    # ----- HIV -----------------------------------------------------------
    hiv_data = pd.read_csv(DATA / 'zimbabwe_hiv_calib.csv')

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    band(ax, get_series(q_sus, 'hiv', 'prevalence'),
         color=COL_MODEL, mult=100, label='Model (whole pop) 5-95%')
    s_1549 = get_series(q_sus, 'hiv', 'prevalence_15_49')
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
    band(ax, get_series(q_sus, 'hiv', 'new_infections'),
         color=COL_MODEL, mult=1e-3)
    ax.scatter(hiv_data['time'], hiv_data['hiv_new_infections'] * 1e-3,
               color=COL_DATA, marker='o', s=25, zorder=10,
               edgecolor='white', linewidth=0.6, label='UNAIDS')
    ax.set_ylabel('New HIV inf (thousands/yr)')
    ax.set_xlabel('Year')
    ax.set_title('HIV incidence')
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    ax.set_ylim(bottom=0)

    fig.suptitle(f'Coverage check, sustained subset '
                 f'(Fix C, {len(sustained_draws)}/{n_total} draws): HIV',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    out = FIG / 'fig2_hiv_coverage_sustained.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    # ----- Other STIs ----------------------------------------------------
    sti_data = pd.read_csv(DATA / 'zimbabwe_sti_data.csv')

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    diseases = [('ng', 'Gonorrhoea (NG)', 'prevalence', 'ng_prevalence'),
                ('ct', 'Chlamydia (CT, F 25–29)', 'prevalence_f_25_30',
                 'ct_prevalence_f_25_30'),
                ('tv', 'Trichomoniasis (TV)', 'prevalence', 'tv_prevalence')]
    for ax, (dname, dlabel, model_col, data_col) in zip(axes, diseases):
        band(ax, get_series(q_sus, dname, model_col),
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

    fig.suptitle(f'Coverage check, sustained subset '
                 f'(Fix C, {len(sustained_draws)}/{n_total} draws): NG/CT/TV',
                 fontsize=13, y=1.02)
    fig.tight_layout()
    out = FIG / 'fig3_sti_coverage_sustained.png'
    fig.savefig(out, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f'  → {out.name}')

    # ----- Headline numbers on sustained subset --------------------------
    print('\n=== HEADLINE: sustained-only quantiles ===')
    print(f'(sustained = mean syph new_inf 2030-2040 > 0; n={len(sustained_draws)})')
    for disease, rn, year, data_str in [
        ('syph', 'trep_prevalence_15_64', 2016, 'ZIMPHIA 0.027'),
        ('syph', 'nontrep_prevalence_15_64', 2016, 'ZIMPHIA 0.008'),
        ('syph', 'prevalence_sw', 2019, 'target 0.20-0.40'),
        ('hiv', 'prevalence', 2010, 'UNAIDS ~0.13'),
        ('hiv', 'prevalence_15_49', 2016, 'ZIMPHIA 0.159'),
    ]:
        s = get_series(q_sus, disease, rn)
        if s is None:
            continue
        row = s[s['year'] == year]
        if len(row) == 0:
            continue
        row = row.iloc[0]
        print(f'  {disease:5s} {rn:30s} {year}: med={row["median"]:.4f}  '
              f'5-95=[{row["ci95_lo"]:.4f}, {row["ci95_hi"]:.4f}]   {data_str}')


if __name__ == '__main__':
    main()
