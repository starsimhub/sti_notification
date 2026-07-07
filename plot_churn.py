"""Churn story: why POC-alone doesn't reduce CT prevalence/incidence.

Two panels (slide format, 12.15w x 5h), from results/churn_ct.csv
(diagnostics/churn_tracer.py):
  Left   reinfection-free survival after a successful cure (months since cure),
         SOC vs POC overlaid -- cures don't stick, and POC doesn't change it.
  Right  source of the reinfections: sex-work reservoir (FSW/client) vs general
         partners -- the reservoir POC-at-care never reaches.

House style (Libertinus Sans), no figure title.
  conda run -n starsim python plot_churn.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent
CSV = REPO / 'results' / 'churn_ct.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

GREY, BLUE = '#9aa0a6', '#4a90d9'
ARM_C = {'SOC': GREY, 'POC': BLUE}
FUP = 36
# infector category -> reservoir grouping for the source panel
SRC_GROUP = {'fsw': 'sex-work network', 'client': 'sex-work network',
             'f_other': 'general partner', 'm_other': 'general partner'}
GROUP_C = {'general partner': '#e0a458', 'sex-work network': '#c0392b'}


def set_font(size=12):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def survival(df_arm, horizon=FUP):
    """% of cured cohort still infection-free at each month 0..horizon."""
    n = len(df_arm)
    months = np.arange(0, horizon + 1)
    reinf_by = np.array([((df_arm.months <= m) & df_arm.reinfected).sum() for m in months])
    return months, 100 * (1 - reinf_by / max(n, 1))


def main():
    set_font(12)
    df = pd.read_csv(CSV)
    df['group'] = df.src_cat.map(SRC_GROUP)

    fig, (axS, axR) = pl.subplots(1, 2, figsize=(12.15, 5),
                                  gridspec_kw={'width_ratios': [1.35, 1]})

    # ---- left: reinfection-free survival after cure ----
    end = {}
    for arm in ('SOC', 'POC'):
        d = df[df.arm == arm]
        m, s = survival(d)
        axS.plot(m, s, color=ARM_C[arm], lw=2.4, label=arm)
        end[arm] = s[-1]
    # SOC and POC coincide -- one combined endpoint annotation
    axS.text(FUP + 0.7, np.mean(list(end.values())),
             f'{np.mean(list(end.values())):.0f}% clear\nat 36 mo\n(SOC = POC)',
             va='center', fontsize=9.5, color='#444', linespacing=1.15)
    axS.set_xlim(0, FUP + 8); axS.set_ylim(0, 100)
    axS.set_xticks(np.arange(0, FUP + 1, 6))
    axS.set_xlabel('months since successful treatment', fontsize=11)
    axS.set_ylabel('% of cured patients still infection-free', fontsize=11)
    axS.set_title('Cures do not stick', fontsize=14, color=BLUE, pad=8)
    axS.legend(fontsize=10.5, frameon=False, loc='upper right')
    axS.spines[['top', 'right']].set_visible(False)
    axS.tick_params(labelsize=9.5)
    # median time-to-reinfection markers
    for arm in ('SOC', 'POC'):
        med = df.loc[(df.arm == arm) & df.reinfected, 'months'].median()
        if np.isfinite(med):
            axS.plot([med, med], [0, 50], color=ARM_C[arm], lw=0.8, ls=':')
    axS.text(0.5, 6, 'dotted = median time to reinfection', fontsize=8.5,
             color='#666', style='italic')

    # ---- right: source of reinfection (POC arm) ----
    groups = ['general partner', 'sex-work network']
    poc = df[(df.arm == 'POC') & df.reinfected]
    shares = [100 * (poc.group == g).sum() / max(len(poc), 1) for g in groups]
    y = np.arange(len(groups))[::-1]
    for yi, g, sh in zip(y, groups, shares):
        axR.barh(yi, sh, color=GROUP_C[g], height=0.55, zorder=3)
        axR.text(sh + 1.5, yi, f'{sh:.0f}%', va='center', fontsize=11,
                 color=GROUP_C[g])
        axR.text(-2, yi, g, va='center', ha='right', fontsize=10.5, color='#333')
    axR.set_xlim(0, 100); axR.set_ylim(-0.6, len(groups) - 0.4)
    axR.set_yticks([])
    axR.set_xlabel('% of reinfections', fontsize=11)
    axR.set_title('Reinfection comes from the untreated reservoir',
                  fontsize=14, color='#555', pad=8)
    axR.spines[['top', 'right', 'left']].set_visible(False)
    axR.tick_params(labelsize=9.5)

    fig.text(0.5, 0.045,
             'Chlamydia, exp 06 baseline (1 draw x 5 seeds), SOC vs POC-plain, baseline PN fixed in both arms. '
             'Cohort = agents successfully treated in 2028-37, 36-month follow-up.',
             ha='center', fontsize=8, color='#666666')
    fig.text(0.5, 0.018,
             'POC clears more infections but the cure does not persist (median time to reinfection ~6 months, identical to SOC). '
             'Reinfection from the untreated partner reservoir refills the pool -- a clinic-based test reaches none of these partners.',
             ha='center', fontsize=8, color='#666666')
    fig.subplots_adjust(left=0.06, right=0.93, top=0.9, bottom=0.17, wspace=0.18)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_churn.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
