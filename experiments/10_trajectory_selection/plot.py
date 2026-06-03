"""
Posterior predictive plot: overlay posterior ensemble trajectories
on calibration data, plus parameter marginals from the posterior vs NROY.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sciris as sc

OUTPUTS = Path(__file__).parent / 'outputs'
DATA = Path(__file__).resolve().parents[2] / 'data'
FIGURES = Path(__file__).parent / 'figures'
NROY_CSV = Path(__file__).resolve().parents[1] / '09_history_matching' / 'outputs' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'


def plot_posterior_predictive():
    """Bar chart comparing posterior target medians + 90% CI to observations."""
    df = pd.read_csv(OUTPUTS / 'weighted_results.csv')
    w = df['weight'].values

    observations = {
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

    fig, ax = plt.subplots(figsize=(14, 5))
    x = np.arange(len(observations))
    labels = []
    obs_vals = []
    medians = []
    lo5 = []
    hi95 = []

    for col, (obs, label) in observations.items():
        vals = df[col].values
        # Weighted quantiles via resampling
        idx = np.random.choice(len(vals), size=10000, replace=True, p=w)
        resampled = vals[idx]
        medians.append(np.median(resampled))
        lo5.append(np.percentile(resampled, 5))
        hi95.append(np.percentile(resampled, 95))
        obs_vals.append(obs)
        labels.append(label)

    medians = np.array(medians)
    lo5 = np.array(lo5)
    hi95 = np.array(hi95)
    obs_vals = np.array(obs_vals)

    ax.bar(x, medians, width=0.4, color='steelblue', alpha=0.7, label='Posterior median')
    ax.errorbar(x, medians, yerr=[medians - lo5, hi95 - medians],
                fmt='none', color='steelblue', capsize=3, label='90% CI')
    ax.scatter(x, obs_vals, color='C3', s=40, zorder=5, label='Data')

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Value')
    ax.set_title('Posterior predictive vs observed data')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / 'posterior_predictive.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "posterior_predictive.png"}')


def plot_parameter_marginals():
    """Compare NROY marginals (prior within NROY) to posterior marginals."""
    nroy = pd.read_csv(NROY_CSV)
    posterior = pd.read_csv(OUTPUTS / 'posterior_ensemble.csv')

    # Parameter columns present in both
    par_cols_nroy = [c for c in nroy.columns if c in [
        'hiv.beta_m2f', 'log_syph.beta_m2f', 'log_ng.beta_m2f',
        'log_ct.beta_m2f', 'log_tv.beta_m2f',
        'structuredsexual.prop_f0', 'structuredsexual.m1_conc',
        'structuredsexual.dur_sw',
    ]]

    # The posterior CSV has draw_idx — need to map back to NROY params
    # Use draw_idx to look up NROY params
    posterior_pars = nroy.iloc[posterior['draw_idx'].values].reset_index(drop=True)

    ncols = 4
    nrows = 2
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 7))
    axes = axes.ravel()

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

    for ax, col in zip(axes, par_cols_nroy):
        ax.hist(nroy[col], bins=30, density=True, alpha=0.4, color='grey', label='NROY')
        ax.hist(posterior_pars[col], bins=30, density=True, alpha=0.6, color='steelblue', label='Posterior')
        ax.set_title(labels.get(col, col), fontsize=10)
        ax.spines[['top', 'right']].set_visible(False)
        if ax == axes[0]:
            ax.legend(fontsize=8)

    fig.suptitle('Parameter marginals: NROY (grey) vs Posterior (blue)', fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'parameter_marginals.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "parameter_marginals.png"}')


if __name__ == '__main__':
    plot_posterior_predictive()
    plot_parameter_marginals()
