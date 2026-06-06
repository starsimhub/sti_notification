"""
Three figures for exp 19:
1. Sero/detect ratio vs time_to_undetectable — the headline. One line per
   draw, crossing the data ratio line. Identifies the grid value(s) where
   model matches data.
2. Absolute detect_f and sero_f vs time_to_undetectable — verifies that
   the right ratio comes with absolute levels in the data ballpark, not
   at some weird (0.001 / 0.003) corner.
3. Extinction rate by grid point — informs whether longer
   time_to_undetectable also reduces stochastic extinction.

Bonus diagnostic: model age ORs (15-24 ref, 25-34, 35-49, 50-64) vs
Ruangtragool 2022 cORs, at the best-fit grid value.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sciris as sc

OUTPUTS = Path(__file__).parent / 'outputs'
FIGURES = Path(__file__).parent / 'figures'

DATA_RATIO = 3.0
DATA_DETECT_F = 0.010
DATA_SERO_F   = 0.030

# Ruangtragool 2022 Table — Total cORs (Total population, crude OR).
RUANGTRAGOOL_TOTAL_COR = {
    '15-24': 1.0,
    '25-34': 1.5,
    '35-49': 1.7,
    '50+':   2.5,
}
# Female cOR + Male cOR for sex-specific comparison.
RUANGTRAGOOL_F_COR = {'15-24': 1.0, '25-34': 1.3, '35-49': 1.0, '50+': 1.7}
RUANGTRAGOOL_M_COR = {'15-24': 1.0, '25-34': 2.0, '35-49': 3.6, '50+': 4.7}


def load_results():
    rows = []
    with (OUTPUTS / 'results.jsonl').open() as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df = df[df['status'] == 'ok'].copy()
    df['ratio_f'] = (df['syph_seroprev_15_64_f_2016']
                     / df['syph_detectable_15_64_f_2016'].replace(0, np.nan))
    df['extinct'] = (df['syph_prev_f_2020_2025'] <= 0.001).astype(int)
    return df


def plot_ratio_vs_ttu(df):
    """Headline plot: ratio vs ttu, one line per draw, data ratio overlaid."""
    fig, ax = plt.subplots(figsize=(10, 6))
    cohort_colour = {'top_weighted': 'C0', 'low_ratio': 'C1', 'uniform': 'C2'}
    cohort_label_used = {c: False for c in cohort_colour}

    for draw_idx, sub in df.groupby('draw_idx'):
        sub = sub.sort_values('ttu_mean')
        cohort = sub['cohort'].iloc[0]
        label = cohort if not cohort_label_used[cohort] else None
        cohort_label_used[cohort] = True
        ax.plot(sub['ttu_mean'], sub['ratio_f'],
                color=cohort_colour[cohort], alpha=0.6, marker='o',
                label=label)

    ax.axhline(DATA_RATIO, color='C3', linestyle='--', linewidth=2,
               label=f'Data ratio (3x)')
    ax.set_xlabel('time_to_undetectable mean (years)')
    ax.set_ylabel('Seroprev / Detect ratio (F, 15-64)')
    ax.set_yscale('log')
    ax.set_title('Sero/detect ratio collapses as time_to_undetectable lengthens; '
                 'data band reached at ~15-25y')
    ax.set_xticks([2, 5, 10, 20, 30])
    ax.legend(title='Cohort')
    ax.spines[['top', 'right']].set_visible(False)
    sc.figlayout()
    fig.savefig(FIGURES / 'ratio_vs_ttu.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "ratio_vs_ttu.png"}')


def plot_absolute_levels(df):
    """detect_f and sero_f vs ttu — verify absolute levels match at the right ratio."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    cohort_colour = {'top_weighted': 'C0', 'low_ratio': 'C1', 'uniform': 'C2'}

    for ax, col, data_val, name in [
        (axes[0], 'syph_detectable_15_64_f_2016', DATA_DETECT_F, 'Detect F (15-64)'),
        (axes[1], 'syph_seroprev_15_64_f_2016',   DATA_SERO_F,   'Seroprev F (15-64)'),
    ]:
        cohort_label_used = {c: False for c in cohort_colour}
        for draw_idx, sub in df.groupby('draw_idx'):
            sub = sub.sort_values('ttu_mean')
            cohort = sub['cohort'].iloc[0]
            label = cohort if not cohort_label_used[cohort] else None
            cohort_label_used[cohort] = True
            ax.plot(sub['ttu_mean'], sub[col],
                    color=cohort_colour[cohort], alpha=0.6, marker='o', label=label)
        ax.axhline(data_val, color='C3', linestyle='--', linewidth=2,
                   label=f'Data ({data_val:.3f})')
        ax.set_xlabel('time_to_undetectable mean (years)')
        ax.set_ylabel(name)
        ax.set_yscale('log')
        ax.set_xticks([2, 5, 10, 20, 30])
        ax.set_title(name)
        ax.legend(loc='upper right', fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)
    sc.figlayout()
    fig.savefig(FIGURES / 'absolute_levels.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "absolute_levels.png"}')


def plot_extinction(df):
    """Bar chart of extinction fraction per grid point."""
    fig, ax = plt.subplots(figsize=(9, 5))
    agg = df.groupby('ttu_mean')['extinct'].mean()
    x = np.arange(len(agg))
    ax.bar(x, agg.values, color='steelblue', alpha=0.8)
    for i, v in enumerate(agg.values):
        ax.text(i, v + 0.02, f'{v*100:.0f}%', ha='center', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([f'{int(t)}y' for t in agg.index])
    ax.set_ylabel('Fraction of sims with prev_f_2020-25 < 0.1%')
    ax.set_xlabel('time_to_undetectable mean')
    ax.set_title('Extinction rate by grid point — minimum at 20y but persistent ~40-67%')
    ax.set_ylim(0, 1.0)
    ax.spines[['top', 'right']].set_visible(False)
    sc.figlayout()
    fig.savefig(FIGURES / 'extinction.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "extinction.png"}')


def plot_age_or_diagnostic(df, best_ttu=20.0):
    """Model age cORs (15-24 ref) vs Ruangtragool 2022 data — at best ttu.

    Aggregates across draws at the best ttu grid value (sum detectable
    counts + denominators, compute prevalence per age band, then OR
    against 15-24 band).
    """
    sub = df[df['ttu_mean'] == best_ttu].copy()
    # Pool counts across all draws in the cohort at this ttu.
    bands = [('15-24', 15, 25), ('25-34', 25, 35),
             ('35-49', 35, 50), ('50+', 50, 65)]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (sex_lab, data_dict) in zip(
        axes,
        [('Total', RUANGTRAGOOL_TOTAL_COR),
         ('F',     RUANGTRAGOOL_F_COR),
         ('M',     RUANGTRAGOOL_M_COR)],
    ):
        prev_band = {}
        for band, lo, hi in bands:
            if sex_lab == 'Total':
                n = sub[f'detect_F_{lo}_{hi}_n'].sum() + sub[f'detect_M_{lo}_{hi}_n'].sum()
                pos = sub[f'detect_F_{lo}_{hi}_pos'].sum() + sub[f'detect_M_{lo}_{hi}_pos'].sum()
            else:
                n   = sub[f'detect_{sex_lab}_{lo}_{hi}_n'].sum()
                pos = sub[f'detect_{sex_lab}_{lo}_{hi}_pos'].sum()
            prev_band[band] = pos / n if n > 0 else 0.0

        # Crude OR vs 15-24 = (p_band / (1 - p_band)) / (p_ref / (1 - p_ref)).
        p_ref = prev_band['15-24']
        odds_ref = p_ref / (1 - p_ref) if 0 < p_ref < 1 else np.nan
        model_cors = {}
        for band, lo, hi in bands:
            p = prev_band[band]
            odds = p / (1 - p) if 0 < p < 1 else np.nan
            model_cors[band] = odds / odds_ref if odds_ref and odds_ref > 0 else np.nan

        x = np.arange(len(bands))
        bw = 0.35
        data_vals = [data_dict[b[0]] for b in bands]
        model_vals = [model_cors[b[0]] for b in bands]
        ax.bar(x - bw/2, data_vals, bw, label='Ruangtragool 2022 cOR',
               color='C3', alpha=0.7)
        ax.bar(x + bw/2, model_vals, bw, label='Model cOR',
               color='steelblue', alpha=0.7)
        ax.axhline(1.0, color='k', linestyle=':', alpha=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([b[0] for b in bands])
        ax.set_ylabel('Crude odds ratio (vs 15-24)')
        ax.set_title(f'{sex_lab} (ttu={best_ttu:.0f}y)')
        ax.legend(fontsize=9)
        ax.spines[['top', 'right']].set_visible(False)

    fig.suptitle('Age cORs for detectable syphilis: model (pooled, 15 draws) vs ZIMPHIA',
                 y=1.02)
    sc.figlayout()
    fig.savefig(FIGURES / 'age_or_diagnostic.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "age_or_diagnostic.png"}')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)
    df = load_results()
    plot_ratio_vs_ttu(df)
    plot_absolute_levels(df)
    plot_extinction(df)
    plot_age_or_diagnostic(df, best_ttu=20.0)
