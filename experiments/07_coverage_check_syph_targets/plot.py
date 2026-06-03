"""
Plot prior predictive trajectories against calibration targets.

13 panels: 4 non-syphilis STIs + 9 syphilis indicators (by-sex
prevalence, seroprevalence, ANC, symptomatic, HIV coinfection).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as plt

RESULTS = Path(__file__).parent / 'results'
DATA = Path(__file__).resolve().parents[2] / 'data'

# (model result column, data file, data column, panel title)
TARGETS = [
    # --- Non-syphilis STIs ---
    ('ng.prevalence',          'zimbabwe_sti_data.csv',  'ng_prevalence',           'NG prevalence'),
    ('ct.prevalence_f_25_30',  'zimbabwe_sti_data.csv',  'ct_prevalence_f_25_30',   'CT prevalence (women 25-30)'),
    ('tv.prevalence',          'zimbabwe_sti_data.csv',  'tv_prevalence',           'TV prevalence'),
    ('hiv.prevalence',         'zimbabwe_hiv_calib.csv', 'hiv_prevalence',          'HIV prevalence'),

    # --- Syphilis: current infection by sex (ZIMPHIA 2016) ---
    ('syph.prevalence_f',                'zimbabwe_syph_data.csv', 'syph.prevalence_f',                'Syph prevalence (F, ZIMPHIA)'),
    ('syph.prevalence_m',                'zimbabwe_syph_data.csv', 'syph.prevalence_m',                'Syph prevalence (M, ZIMPHIA)'),

    # --- Syphilis: seroprevalence by sex (ZIMPHIA 2016) ---
    ('syph.serological_prevalence_f',    'zimbabwe_syph_data.csv', 'syph.serological_prevalence_f',    'Syph seroprevalence (F, ZIMPHIA)'),
    ('syph.serological_prevalence_m',    'zimbabwe_syph_data.csv', 'syph.serological_prevalence_m',    'Syph seroprevalence (M, ZIMPHIA)'),

    # --- Syphilis: ANC prevalence (BMJ model estimates) ---
    ('syph.pregnant_prevalence',         'zimbabwe_syph_data.csv', 'syph.pregnant_prevalence',         'Syph ANC prevalence (BMJ)'),

    # --- Syphilis: symptomatic (primary + secondary), no data ---
    ('syph.active_prevalence',           None,                     None,                               'Syph symptomatic prevalence'),

    # --- HIV-syphilis coinfection (ZIMPHIA 2016) ---
    ('syph_hiv_coinfection.syph_prev_has_hiv', 'zimbabwe_syph_data.csv', 'syph_hiv_coinfection.syph_prev_has_hiv', 'Syph prev | HIV+ (ZIMPHIA)'),
    ('syph_hiv_coinfection.syph_prev_no_hiv',  'zimbabwe_syph_data.csv', 'syph_hiv_coinfection.syph_prev_no_hiv',  'Syph prev | HIV- (ZIMPHIA)'),
]


def plot_coverage(savepath='figures/coverage.png', show=False):
    dfs = sc.load(RESULTS / 'coverage_dfs.obj')

    n_targets = len(TARGETS)
    ncols = 4
    nrows = (n_targets + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows))
    axes = axes.ravel()

    for ax, (col, datafile, datacol, title) in zip(axes, TARGETS):
        # Trajectories
        for df in dfs:
            if col in df.columns:
                ax.plot(df['time'], df[col], color='grey', alpha=0.25, lw=0.8)

        # Data overlay
        if datafile is not None and datacol is not None:
            try:
                data = pd.read_csv(DATA / datafile)
                data = data.dropna(subset=[datacol])
                ax.scatter(data['time'], data[datacol], color='C3', s=18, zorder=5,
                           label='Data')
                ax.legend(loc='best', fontsize=9)
            except (FileNotFoundError, KeyError):
                pass

        ax.set_title(title, fontsize=10)
        ax.set_xlabel('Year')
        ax.set_ylabel(col.split('.')[-1])
        ax.spines[['top', 'right']].set_visible(False)

    # Hide unused subplots
    for i in range(n_targets, len(axes)):
        axes[i].axis('off')

    fig.suptitle(f'Prior predictive coverage check  ({len(dfs)} draws)',
                 fontsize=13, y=1.00)
    sc.figlayout()

    savepath = Path(__file__).resolve().parent / savepath
    savepath.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(savepath, dpi=120, bbox_inches='tight')
    if show:
        plt.show()
    print(f'Saved {savepath}')
    return fig


if __name__ == '__main__':
    plot_coverage()
