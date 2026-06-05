"""
Three figures for exp 13:
1. Posterior predictive bar chart — medians + 90% CI vs data.
2. Parameter marginals — NROY vs posterior.
3. Syphilis bifurcation diagnostic — histogram of late-window syph_f
   across all 1000 sims, showing the extinct / over-sustained two modes
   that the posterior cannot resolve.
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
NROY_CSV = Path(__file__).resolve().parents[1] / '09_history_matching' / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'

OBS_LABELS = {
    'hiv_prev_2000_2010':     (0.116, 'HIV 2000-10'),
    'hiv_prev_2010_2020':     (0.092, 'HIV 2010-20'),
    'ng_prev_2005_2015':      (0.020, 'NG 2005-15'),
    'ct_prev_f2530':          (0.120, 'CT F25-30'),
    'tv_prev_2005_2015':      (0.111, 'TV 2005-15'),
    'syph_prev_f_2016':       (0.010, 'Syph F'),
    'syph_prev_m_2016':       (0.006, 'Syph M'),
    'syph_seroprev_f_2016':   (0.030, 'Sero F'),
    'syph_seroprev_m_2016':   (0.024, 'Sero M'),
    'syph_anc_2000_2015':     (0.020, 'ANC'),
    'syph_prev_hivpos_2016':  (0.029, 'S|HIV+'),
    'syph_prev_hivneg_2016':  (0.004, 'S|HIV-'),
}


def plot_posterior_predictive():
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    w = df['weight'].values
    rng = np.random.default_rng(0)

    fig, ax = plt.subplots(figsize=(14, 5))
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

    ax.bar(x, medians, width=0.4, color='steelblue', alpha=0.7, label='Posterior median')
    ax.errorbar(x, medians, yerr=[medians - lo5, hi95 - medians],
                fmt='none', color='steelblue', capsize=3, label='90% CI')
    ax.scatter(x, obs_vals, color='C3', s=40, zorder=5, label='Data')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Value')
    ax.set_title(f'Posterior predictive (ESS={1.0/(w**2).sum():.1f}/{len(w)}) vs observations')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / 'posterior_predictive.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "posterior_predictive.png"}')


def plot_parameter_marginals():
    nroy = pd.read_csv(NROY_CSV)
    posterior = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')

    par_cols = [c for c in nroy.columns if c in {
        'hiv.beta_m2f', 'log_syph.beta_m2f', 'log_ng.beta_m2f',
        'log_ct.beta_m2f', 'log_tv.beta_m2f',
        'structuredsexual.prop_f0', 'structuredsexual.m1_conc',
        'structuredsexual.dur_sw',
    }]
    posterior_pars = nroy.iloc[posterior['draw_idx'].astype(int).values].reset_index(drop=True)

    labels = {
        'hiv.beta_m2f': 'HIV beta',
        'log_syph.beta_m2f': 'log Syph beta',
        'log_ng.beta_m2f': 'log NG beta',
        'log_ct.beta_m2f': 'log CT beta',
        'log_tv.beta_m2f': 'log TV beta',
        'structuredsexual.prop_f0': 'prop_f0',
        'structuredsexual.m1_conc': 'm1_conc',
        'structuredsexual.dur_sw': 'dur_sw',
    }

    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    axes = axes.ravel()
    for ax, col in zip(axes, par_cols):
        ax.hist(nroy[col], bins=30, density=True, alpha=0.4, color='grey', label='NROY')
        ax.hist(posterior_pars[col], bins=30, density=True, alpha=0.6, color='steelblue', label='Posterior')
        ax.set_title(labels.get(col, col), fontsize=10)
        ax.spines[['top', 'right']].set_visible(False)
        if ax is axes[0]:
            ax.legend(fontsize=8)
    fig.suptitle('Parameter marginals: NROY (grey) vs Posterior (blue)', fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'parameter_marginals.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "parameter_marginals.png"}')


def plot_syph_bifurcation():
    """Distribution of late-window female syphilis prevalence across all sims.

    Shows the two-mode pattern (extinct vs over-sustained) that the
    importance-weighting cannot resolve.
    """
    rows = []
    with (OUTPUTS / 'results.jsonl').open() as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df = df[df['status'] == 'ok'].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: histogram of syph_prev_f_2020_2025 across all 1000 sims.
    vals = df['syph_prev_f_2020_2025'].values
    extinct = vals <= 0.001
    alive = ~extinct
    bins = np.linspace(0, max(0.25, np.nanmax(vals) * 1.05), 60)
    ax = axes[0]
    ax.hist(vals[alive], bins=bins, color='steelblue', alpha=0.7,
            label=f'Sustaining ({alive.sum()})')
    ax.hist(vals[extinct], bins=bins, color='darkred', alpha=0.7,
            label=f'Extinct ({extinct.sum()})')
    ax.axvline(0.010, color='C3', linestyle='--', linewidth=1.5,
               label='Data (1.0%)')
    ax.axvline(0.005, color='grey', linestyle=':', linewidth=1,
               label='Filter floor (0.5%)')
    ax.set_xlabel('Female syphilis prevalence, mean 2020–2025')
    ax.set_ylabel('Count of NROY draws')
    ax.set_title('Late-window syphilis: extinct vs over-sustained bifurcation')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    # Right: scatter of syph_prev_f_2016 (calibration target) vs
    # syph_prev_f_2020_2025 (post-calibration window). Shows whether
    # 2016 calibration informs 2020-2025 dynamics.
    ax = axes[1]
    sc_col = ['darkred' if e else 'steelblue' for e in extinct]
    ax.scatter(df['syph_prev_f_2016'], df['syph_prev_f_2020_2025'],
               c=sc_col, alpha=0.4, s=12)
    ax.axvline(0.010, color='C3', linestyle='--', linewidth=1, label='Data 2016 (1.0%)')
    ax.axhline(0.010, color='C3', linestyle='--', linewidth=1)
    ax.set_xlabel('Syph prev F at 2016 (calibration target)')
    ax.set_ylabel('Syph prev F mean 2020-2025')
    ax.set_title('2016 target vs late-window dynamics')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'syph_bifurcation.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "syph_bifurcation.png"}')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_posterior_predictive()
    plot_parameter_marginals()
    plot_syph_bifurcation()
