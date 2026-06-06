"""
Four figures for exp 21:
1. Posterior predictive bar chart — medians + 90% CI vs data on 10 targets.
2. Parameter marginals — NROY vs posterior across the 9 parameters,
   including time_to_undetectable.
3. Sero/detect ratio diagnostic — direct comparison to exp 18's same
   figure. Shows the model now sits on the data ratio (~3-4x), not the
   30x corner exp 18 was driven into.
4. Late-window extinction diagnostic — distribution of prev_f_2020-2025
   in alive pool vs posterior. The caveat figure.
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
NROY_CSV = (Path(__file__).resolve().parents[1]
            / '20_history_matching_9param'
            / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv')

OBS_LABELS = {
    'hiv_prev_2000_2010':           (0.116, 'HIV 2000-10'),
    'hiv_prev_2010_2020':           (0.092, 'HIV 2010-20'),
    'ng_prev_2005_2015':            (0.020, 'NG 2005-15'),
    'ct_prev_f2530':                (0.120, 'CT F25-30'),
    'tv_prev_2005_2015':            (0.111, 'TV 2005-15'),
    'syph_detectable_15_64_f_2016': (0.010, 'Detect F'),
    'syph_detectable_15_64_m_2016': (0.006, 'Detect M'),
    'syph_seroprev_15_64_f_2016':   (0.030, 'Sero F'),
    'syph_seroprev_15_64_m_2016':   (0.024, 'Sero M'),
    'syph_anc_2000_2015':           (0.020, 'ANC'),
}


def plot_posterior_predictive():
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    w = df['weight'].values
    rng = np.random.default_rng(0)

    fig, ax = plt.subplots(figsize=(13, 5))
    x = np.arange(len(OBS_LABELS))
    labels, obs_vals, medians, lo5, hi95 = [], [], [], [], []

    for col, (obs, label) in OBS_LABELS.items():
        vals = df[col].values
        idx = rng.choice(len(vals), size=10000, replace=True, p=w)
        resampled = vals[idx]
        medians.append(np.median(resampled))
        lo5.append(np.percentile(resampled, 5))
        hi95.append(np.percentile(resampled, 95))
        obs_vals.append(obs)
        labels.append(label)

    medians, lo5, hi95, obs_vals = map(np.array, (medians, lo5, hi95, obs_vals))
    yerr = np.vstack([medians - lo5, hi95 - medians])

    ax.errorbar(x - 0.15, medians, yerr=yerr, fmt='o', color='steelblue',
                capsize=4, label='Posterior median (90% CI)', markersize=7)
    ax.scatter(x + 0.15, obs_vals, marker='s', s=70, color='C3',
               label='Data target', zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha='right')
    ax.set_ylabel('Prevalence')
    summary = json.loads((OUTPUTS / 'summary.json').read_text())
    ax.set_title(f'Posterior predictive on 10 targets — ESS={summary["ess"]:.0f}, '
                 f'ratio={summary["ess_ratio"]*100:.1f}% (vs exp 18: 4.8, 1.2%)')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'posterior_predictive.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "posterior_predictive.png"}')


def plot_parameter_marginals():
    post = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')
    nroy = pd.read_csv(NROY_CSV)
    nroy['draw_idx'] = nroy.index
    post_pars = post.merge(nroy, on='draw_idx', how='left', suffixes=('_t', ''))

    param_cols = ['hiv.beta_m2f', 'log_syph.beta_m2f', 'syph.time_to_undetectable',
                  'log_ng.beta_m2f', 'log_ct.beta_m2f', 'log_tv.beta_m2f',
                  'structuredsexual.prop_f0', 'structuredsexual.m1_conc',
                  'structuredsexual.dur_sw']

    fig, axes = plt.subplots(3, 3, figsize=(15, 11))
    axes = axes.flat
    for ax, col in zip(axes, param_cols):
        bins = np.linspace(nroy[col].min(), nroy[col].max(), 30)
        ax.hist(nroy[col], bins=bins, color='lightgrey',
                edgecolor='grey', label='NROY (1000)', density=True)
        ax.hist(post_pars[col], bins=bins, color='steelblue', alpha=0.7,
                label='Posterior (500)', density=True)
        # Annotate medians
        nm = nroy[col].median()
        pm = post_pars[col].median()
        ax.axvline(nm, color='grey', linestyle='--', alpha=0.7, linewidth=1)
        ax.axvline(pm, color='steelblue', linestyle='-', alpha=0.9, linewidth=1.5)
        ax.set_title(f'{col}\nNROY={nm:.3f} / Post={pm:.3f}', fontsize=9)
        ax.set_ylabel('Density', fontsize=8)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(axis='both', labelsize=8)
    axes[0].legend(fontsize=8, loc='upper right')
    fig.suptitle('Parameter marginals: NROY vs reweighted posterior — '
                 'time_to_undetectable centres at ~20y in both')
    sc.figlayout()
    fig.savefig(FIGURES / 'parameter_marginals.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "parameter_marginals.png"}')


def plot_sero_detect_ratio():
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    post = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: scatter of alive draws (size = weight, colour = log_lik).
    ax = axes[0]
    sizes = 10 + 200 * df['weight'].values / df['weight'].max()
    sc1 = ax.scatter(df['syph_detectable_15_64_f_2016'],
                     df['syph_seroprev_15_64_f_2016'],
                     s=sizes, c=df['log_lik'], cmap='viridis', alpha=0.5,
                     edgecolor='none')
    ax.scatter([0.010], [0.030], s=300, marker='*', color='C3',
               edgecolor='black', linewidth=1.5, zorder=5, label='Data')

    x_line = np.linspace(0.0005, 0.05, 100)
    ax.plot(x_line, 3 * x_line, 'k--', alpha=0.6, label='sero = 3 × detect (data ratio)')

    ax.set_xlabel('Detectable prevalence F (15-64, 2016)')
    ax.set_ylabel('Seroprevalence F (15-64, 2016)')
    ax.set_title(f'Alive pool (n={len(df)}) — sits on the data ratio line, '
                 'not the 30x corner exp 18 was driven into')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(5e-4, 0.05)
    ax.set_ylim(5e-3, 0.1)
    ax.legend(loc='lower right', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    plt.colorbar(sc1, ax=ax, label='log-likelihood')

    # Right: ratio histogram.
    ax = axes[1]
    ratio_alive = (df['syph_seroprev_15_64_f_2016']
                   / df['syph_detectable_15_64_f_2016']).replace(
        [np.inf, -np.inf], np.nan).dropna()
    ratio_post = (post['syph_seroprev_15_64_f_2016']
                  / post['syph_detectable_15_64_f_2016']).replace(
        [np.inf, -np.inf], np.nan).dropna()
    bins = np.logspace(np.log10(0.5), np.log10(100), 40)
    ax.hist(ratio_alive, bins=bins, color='lightgrey', edgecolor='grey',
            alpha=0.8, label=f'Alive pool (median {ratio_alive.median():.1f}x)')
    ax.hist(ratio_post, bins=bins, color='steelblue', alpha=0.7,
            label=f'Posterior (median {ratio_post.median():.1f}x)')
    ax.axvline(3, color='C3', linestyle='--', linewidth=2, label='Data ratio (3x)')
    ax.set_xscale('log')
    ax.set_xlabel('Seroprev F / Detectable F ratio')
    ax.set_ylabel('Count')
    ax.set_title('Invisible-reservoir ratio: alive pool + posterior vs data')
    ax.legend()
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'sero_detect_ratio.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "sero_detect_ratio.png"}')


def plot_late_window_extinction():
    """Distribution of 2020-2025 prev_f in alive pool vs posterior.

    The caveat figure: even though calibration brackets all 10 targets at
    2016, a meaningful fraction of posterior draws are extincting by 2025.
    """
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    post = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')

    fig, ax = plt.subplots(figsize=(11, 5))
    bins = np.linspace(0, 0.25, 40)
    ax.hist(df['syph_prev_f_2020_2025'], bins=bins, color='lightgrey',
            edgecolor='grey', alpha=0.8,
            label=f'Alive pool (mean {df["syph_prev_f_2020_2025"].mean()*100:.2f}%, '
                  f'extinct frac {(df["syph_prev_f_2020_2025"] < 0.001).mean()*100:.0f}%)')
    ax.hist(post['syph_prev_f_2020_2025'], bins=bins, color='steelblue', alpha=0.7,
            label=f'Posterior (mean {post["syph_prev_f_2020_2025"].mean()*100:.2f}%, '
                  f'extinct frac {(post["syph_prev_f_2020_2025"] < 0.001).mean()*100:.0f}%)')

    ax.set_xlabel('Syph prevalence F, mean 2020-2025')
    ax.set_ylabel('Count')
    ax.set_title('Late-window syph dynamics: posterior preferentially picks '
                 'low-sustaining draws that extinguish by 2025')
    ax.legend()
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'late_window_extinction.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "late_window_extinction.png"}')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_posterior_predictive()
    plot_parameter_marginals()
    plot_sero_detect_ratio()
    plot_late_window_extinction()
