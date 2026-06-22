"""
Care cascade figure for the STI undertreatment story.

Hypothesis being articulated: under syndromic management, most women with a
treatable STI are never cured. This builds the cascade that shows why, per
100 incident chlamydia infections in women, in the style of
syph_dx_zim/plot_fig2_treatment.py::plot_gud_cascade.

Step provenance (all from the Zimbabwe model, draw 773):
  Symptomatic         p_symp (women, CT)              = 0.30   [model.make_discharging_stis]
  Seek care           p_symp_care (women, CT)         = 0.49   [model.make_discharging_stis]
  Correctly treated   syndromic VDS routing to NG/CT  = 0.70   [SYNDROMIC_TX_MIX_CERV: all3 0.50 + ngct 0.20]
                      x treatment efficacy            = 0.90   [STITreatment.treat_eff]
  Cured at 12 months  1 - reinfection rate                     [measured, exp 04 chains_A.csv]

Numbers are preliminary (single draw, single seed); regenerate against the
sustained ensemble for final magnitudes.
"""
import sciris as sc
import numpy as np
import pandas as pd
import matplotlib.pyplot as pl

FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'
REINF_CSV = 'experiments/04_soc_vs_poc_pn_wiring/outputs/chains_A.csv'
FIGURES_DIR = 'figures'

BAR_COLOR = '#4a90d9'
LOSS_COLOR = '#dddddd'

# --- cascade inputs (documented above) ---
P_SYMP_F = 0.30
P_SEEK_CARE_F = 0.49
P_ROUTE_NGCT = 0.70
P_CURE_IF_TREATED = 0.90


def set_font(size=None):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def reinfection_rate():
    ch = pd.read_csv(REINF_CSV)
    return float(ch.A_reinfected.mean())


def plot_cascade(ax, steps, labels, loss_labels, title, xmax=115):
    """Horizontal waterfall cascade, matching plot_gud_cascade."""
    y = np.arange(len(steps))[::-1]
    ax.barh(y, steps, color=BAR_COLOR, alpha=0.85, edgecolor='white',
            linewidth=0.5, height=0.7)
    for i in range(1, len(steps)):
        ax.barh(y[i], steps[i-1] - steps[i], left=steps[i],
                color=LOSS_COLOR, alpha=0.5, height=0.7)
    for i, step in enumerate(steps):
        txt = f'{step:.0f}' if step >= 1 else f'{step:.1f}'
        ax.text(step + 1.5, y[i], txt, ha='left', va='center',
                fontsize=16, fontweight='bold')
    for i in range(1, len(steps)):
        lost = steps[i-1] - steps[i]
        if lost > 0.5:
            # left-align just past the retained bar so labels clear the y-axis
            # labels even when the cascade is steep and bars are short
            ax.text(steps[i] + 1.5, y[i] + 0.34, f'−{lost:.0f}: {loss_labels[i]}',
                    ha='left', va='bottom', fontsize=12, color='#888888',
                    style='italic')
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, xmax)
    ax.set_xlabel('per 100 incident infections')
    ax.set_title(title)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def ct_cascade_steps(p_reinf):
    s1 = 100.0
    s2 = s1 * P_SYMP_F
    s3 = s2 * P_SEEK_CARE_F
    s4 = s3 * P_ROUTE_NGCT * P_CURE_IF_TREATED
    s5 = s4 * (1 - p_reinf)
    steps = [s1, s2, s3, s4, s5]
    labels = ['Acquire\ninfection', 'Symptomatic', 'Seek\ncare',
              'Correctly\ntreated', 'Cured at\n12 months']
    loss_labels = ['', 'Asymptomatic', 'No care sought',
                   'Not treated or treatment failure', 'Reinfected within 12 months']
    return steps, labels, loss_labels


if __name__ == '__main__':
    sc.makepath(FIGURES_DIR)
    set_font(size=20)
    p_reinf = reinfection_rate()
    steps, labels, loss_labels = ct_cascade_steps(p_reinf)

    fig, ax = pl.subplots(1, 1, figsize=(12, 6))
    plot_cascade(ax, steps, labels, loss_labels,
                 title='Chlamydia care cascade, women\nunder syndromic management, Zimbabwe model')
    fig.text(0.04, -0.02,
             'Per 100 incident infections. Steps from model parameters '
             '(symptomatic 0.30, seek care 0.49, syndromic routing 0.70, cure 0.90); '
             f'reinfection {p_reinf:.0%} measured (exp 04). Preliminary: draw 773, single seed.',
             fontsize=11, color='#888888', ha='left')
    pl.tight_layout()
    out = f'{FIGURES_DIR}/fig_cascade_ct_soc.png'
    pl.savefig(out, dpi=200, bbox_inches='tight')
    print(f'cured-at-12mo per 100 incident: {steps[-1]:.1f}')
    print(f'Saved {out}')
