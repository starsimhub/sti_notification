"""
Plot prior predictive trajectories from results/coverage_dfs.obj against
the calibration target data.

For each calibration target, draws every prior trajectory in light grey
and overlays the data points. The question this answers: does the
ensemble of trajectories from prior draws bracket the data? If not, the
prior is too narrow, the model is misspecified, or both — and that's a
blocker for any subsequent calibration wave.
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

# Result column → (data file, data column, panel title)
TARGETS = [
    ('ng.prevalence',          'zimbabwe_sti_data.csv',  'ng_prevalence',           'NG prevalence'),
    ('ct.prevalence_f_25_30',  'zimbabwe_sti_data.csv',  'ct_prevalence_f_25_30',   'CT prevalence (women 25-30)'),
    ('tv.prevalence',          'zimbabwe_sti_data.csv',  'tv_prevalence',           'TV prevalence'),
    ('hiv.prevalence',         'zimbabwe_hiv_calib.csv', 'hiv_prevalence',          'HIV prevalence'),
    ('syph.active_prevalence', 'zimbabwe_syph_data.csv', 'syph.active_prevalence',  'Syphilis active prevalence'),
]


def plot_coverage(savepath='figures/coverage.png', show=False):
    dfs = sc.load(RESULTS / 'coverage_dfs.obj')

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.ravel()

    for ax, (col, datafile, datacol, title) in zip(axes, TARGETS):
        # Trajectories
        for df in dfs:
            ax.plot(df['time'], df[col], color='grey', alpha=0.25, lw=0.8)

        # Data overlay
        try:
            data = pd.read_csv(DATA / datafile)
            data = data.dropna(subset=[datacol])
            ax.scatter(data['time'], data[datacol], color='C3', s=18, zorder=5,
                       label='Data')
            ax.legend(loc='best', fontsize=9)
        except (FileNotFoundError, KeyError):
            pass

        ax.set_title(title)
        ax.set_xlabel('Year')
        ax.set_ylabel(col.split('.')[-1])
        ax.spines[['top', 'right']].set_visible(False)

    # Hide unused subplot
    axes[5].axis('off')

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
