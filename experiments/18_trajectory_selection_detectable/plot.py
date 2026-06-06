"""
Three figures for exp 18:
1. Posterior predictive bar chart — medians + 90% CI vs data on 10 targets.
2. Parameter marginals — NROY vs posterior.
3. Sero/detect ratio scatter — visualises the structural ceiling under
   default time_to_undetectable. Data sits at sero/detect ≈ 3; model
   posterior at ≈ 30. This is the diagnostic that motivates exp 19.
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
            / '17_history_matching_detectable'
            / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv')

OBS_LABELS = {
    'hiv_prev_2000_2010':     (0.116, 'HIV 2000-10'),
    'hiv_prev_2010_2020':     (0.092, 'HIV 2010-20'),
    'ng_prev_2005_2015':      (0.020, 'NG 2005-15'),
    'ct_prev_f2530':          (0.120, 'CT F25-30'),
    'tv_prev_2005_2015':      (0.111, 'TV 2005-15'),
    'syph_detectable_f_2016': (0.010, 'Detect F'),
    'syph_detectable_m_2016': (0.006, 'Detect M'),
    'syph_seroprev_f_2016':   (0.030, 'Sero F'),
    'syph_seroprev_m_2016':   (0.024, 'Sero M'),
    'syph_anc_2000_2015':     (0.020, 'ANC'),
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
    ax.set_title(f'Posterior predictive on 10 targets (ESS=4.8, ratio=1.2%)')
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

    param_cols = ['hiv.beta_m2f', 'log_syph.beta_m2f', 'log_ng.beta_m2f',
                  'log_ct.beta_m2f', 'log_tv.beta_m2f',
                  'structuredsexual.prop_f0', 'structuredsexual.m1_conc',
                  'structuredsexual.dur_sw']

    fig, axes = plt.subplots(2, 4, figsize=(15, 7))
    axes = axes.flat
    for ax, col in zip(axes, param_cols):
        bins = np.linspace(nroy[col].min(), nroy[col].max(), 30)
        ax.hist(nroy[col], bins=bins, color='lightgrey',
                edgecolor='grey', label='NROY (1000)', density=True)
        ax.hist(post_pars[col], bins=bins, color='steelblue', alpha=0.7,
                label='Posterior (500)', density=True)
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('Density')
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].legend(fontsize=9)
    fig.suptitle('Parameter marginals: NROY vs reweighted posterior')
    sc.figlayout()
    fig.savefig(FIGURES / 'parameter_marginals.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "parameter_marginals.png"}')


def plot_sero_detect_ratio():
    """The diagnostic figure for exp 19's motivation.

    Each sim is a point in (detectable_f, seroprev_f) space.
    Data lives at (0.010, 0.030) — a 3x ratio.
    Posterior lives at (0.001, 0.042) — a 30x ratio.
    The dashed line connecting origin to data is the "right ratio";
    the model's draws fall above it (too much sero per detect).
    """
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    post = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: scatter of all alive draws, posterior weight encoded as colour.
    ax = axes[0]
    sizes = 10 + 200 * df['weight'].values / df['weight'].max()
    sc1 = ax.scatter(df['syph_detectable_f_2016'], df['syph_seroprev_f_2016'],
                     s=sizes, c=df['log_lik'], cmap='viridis', alpha=0.5,
                     edgecolor='none')
    ax.scatter([0.010], [0.030], s=300, marker='*', color='C3',
               edgecolor='black', linewidth=1.5, zorder=5, label='Data')

    # Reference: the sero/detect = 3 line (data ratio).
    x_line = np.linspace(0.0001, 0.15, 100)
    ax.plot(x_line, 3 * x_line, 'k--', alpha=0.6, label='sero = 3 × detect (data ratio)')
    ax.plot(x_line, 30 * x_line, ':', color='grey', alpha=0.6, label='sero = 30 × detect (model)')

    ax.set_xlabel('Detectable prevalence F (2016)')
    ax.set_ylabel('Seroprevalence F (2016)')
    ax.set_title(f'Alive pool (n={len(df)}) — colour = log-likelihood, size = weight')
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1e-4, 0.2)
    ax.set_ylim(1e-3, 0.5)
    ax.legend(loc='lower right', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    plt.colorbar(sc1, ax=ax, label='log-likelihood')

    # Right: ratio histogram.
    ax = axes[1]
    ratio_alive = (df['syph_seroprev_f_2016'] / df['syph_detectable_f_2016']).replace(
        [np.inf, -np.inf], np.nan).dropna()
    ratio_post = (post['syph_seroprev_f_2016'] / post['syph_detectable_f_2016']).replace(
        [np.inf, -np.inf], np.nan).dropna()
    bins = np.logspace(np.log10(0.5), np.log10(500), 40)
    ax.hist(ratio_alive, bins=bins, color='lightgrey', edgecolor='grey',
            alpha=0.8, label=f'Alive pool (median {ratio_alive.median():.1f}x)')
    ax.hist(ratio_post, bins=bins, color='steelblue', alpha=0.7,
            label=f'Posterior (median {ratio_post.median():.1f}x)')
    ax.axvline(3, color='C3', linestyle='--', linewidth=2, label='Data ratio (3x)')
    ax.set_xscale('log')
    ax.set_xlabel('Seroprev F / Detectable F ratio')
    ax.set_ylabel('Count')
    ax.set_title('Invisible-reservoir ratio: data vs model posterior')
    ax.legend()
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'sero_detect_ratio.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "sero_detect_ratio.png"}')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_posterior_predictive()
    plot_parameter_marginals()
    plot_sero_detect_ratio()
