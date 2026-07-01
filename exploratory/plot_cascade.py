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
# Paths below are relative to repo root; run this script from the repo root.
REINF_CSV = 'archive/04_soc_vs_poc_pn_wiring/outputs/chains_A.csv'
FIGURES_DIR = 'figures'  # fig_cascades_4panel_soc.png (Slide 1)
FIGURES_ARCHIVE = 'figures/archive'  # secondary cascade figures (superseded)

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


def plot_cascade(ax, steps, labels, loss_labels, title, xmax=115,
                 xlabel='per 100 incident infections', show_loss=True,
                 count_fs=16, loss_fs=12, title_fs=None):
    """Horizontal waterfall cascade, matching plot_gud_cascade.

    show_loss=False keeps the grey loss tracks but drops the per-step text
    (for small multi-panel layouts). count_fs/loss_fs scale the labels.
    """
    y = np.arange(len(steps))[::-1]
    ax.barh(y, steps, color=BAR_COLOR, alpha=0.85, edgecolor='white',
            linewidth=0.5, height=0.7)
    for i in range(1, len(steps)):
        ax.barh(y[i], steps[i-1] - steps[i], left=steps[i],
                color=LOSS_COLOR, alpha=0.5, height=0.7)
    for i, step in enumerate(steps):
        txt = f'{step:.0f}' if step >= 1 else f'{step:.1f}'
        ax.text(step + 1.5, y[i], txt, ha='left', va='center',
                fontsize=count_fs, fontweight='bold')
    if show_loss:
        for i in range(1, len(steps)):
            lost = steps[i-1] - steps[i]
            if lost > 0.5:
                # left-align just past the retained bar so labels clear the
                # y-axis labels even when the cascade is steep and bars short
                ax.text(steps[i] + 1.5, y[i] + 0.34, f'−{lost:.0f}: {loss_labels[i]}',
                        ha='left', va='bottom', fontsize=loss_fs, color='#888888',
                        style='italic')
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, xmax)
    if xlabel:
        ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title, fontsize=title_fs)
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


def vds_cascade_steps():
    """VDS presentation cascade, per 100 women with vaginal discharge symptoms.

    Seek-care is the model care-seeking rate; presumptive NG/CT treatment is
    the syndromic routing. The correct-vs-overtreatment split of those treated
    depends on the true etiology mix of VDS presenters (most discharge is BV,
    not an STI) and is left for the sustained ensemble to measure.
    """
    s1 = 100.0
    s2 = s1 * P_SEEK_CARE_F
    s3 = s2 * P_ROUTE_NGCT
    steps = [s1, s2, s3]
    labels = ['Present with\nVDS', 'Seek\ncare', 'Presumptively\ntreated for\nNG/CT']
    loss_labels = ['', 'No care sought', 'Dismissed or metronidazole only']
    return steps, labels, loss_labels


# Per-pathogen cascade parameters (women), Zimbabwe model.
#   p_symp: symptomatic (for syphilis: visible primary chancre)
#   route:  P(syndromic management routes to the correct treatment | seek care)
#   cure:   treatment efficacy | treated
#   sustained: whether the pathogen persists in draw 773 (else illustrative)
#   reinf_measured: whether the 12-month reinfection step is measured (else provisional)
DISEASES = {
    'ng':   dict(name='Gonorrhoea',     p_symp=0.13, route=0.70, cure=0.96, sustained=False),
    'ct':   dict(name='Chlamydia',      p_symp=0.30, route=0.70, cure=0.90, sustained=True),
    'tv':   dict(name='Trichomoniasis', p_symp=0.60, route=0.65, cure=0.90, sustained=False),
    'syph': dict(name='Syphilis',       p_symp=0.30, route=0.80, cure=0.98, sustained=True),
}
SHORT_LABELS = ['Acquired', 'Symptomatic', 'Sought care', 'Treated', 'Cured (12mo)']
SHORT_LOSS = ['', 'Asymptomatic', 'No care', 'Not treated', 'Reinfected']


def disease_cascade_steps(disease, p_reinf):
    """5-step care cascade per 100 incident infections, for a pathogen."""
    d = DISEASES[disease]
    s1 = 100.0
    s2 = s1 * d['p_symp']
    s3 = s2 * P_SEEK_CARE_F
    s4 = s3 * d['route'] * d['cure']
    s5 = s4 * (1 - p_reinf)
    return [s1, s2, s3, s4, s5]


if __name__ == '__main__':
    sc.makepath(FIGURES_DIR)
    set_font(size=20)

    # --- 4-panel cascade by pathogen (NG/CT/TV/syphilis) ---
    p_reinf = reinfection_rate()  # CT-measured; provisional for the others
    fig, axes = pl.subplots(2, 2, figsize=(9.7, 5))
    order = ['ng', 'ct', 'tv', 'syph']
    for ax, dis in zip(axes.flat, order):
        steps = disease_cascade_steps(dis, p_reinf)
        d = DISEASES[dis]
        plot_cascade(ax, steps, SHORT_LABELS, SHORT_LOSS,
                     title=d['name'], xlabel=None, show_loss=False,
                     count_fs=11, title_fs=13)
        ax.tick_params(axis='y', labelsize=10)
        ax.tick_params(axis='x', labelsize=9)
    fig.text(0.5, 0.03,
             'Steps from model parameters (symptomatic, care-seeking 0.49, syndromic routing, cure). '
             f'Reinfection: CT measured ({p_reinf:.0%}); provisional elsewhere. Grey = lost at each step. '
             'Preliminary: draw 66, single seed.',
             fontsize=8, color='#888888', ha='center')
    fig.subplots_adjust(left=0.12, right=0.99, top=0.93, bottom=0.12,
                        wspace=0.34, hspace=0.55)
    out0 = f'{FIGURES_DIR}/fig_cascades_4panel_soc.png'
    fig.savefig(out0, dpi=200)  # no bbox='tight' so the canvas stays exactly 9.7x5
    print(f'Saved {out0}')

    # --- CT care cascade (per 100 incident infections) ---
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
    out = f'{FIGURES_ARCHIVE}/fig_cascade_ct_soc.png'
    pl.savefig(out, dpi=200, bbox_inches='tight')
    print(f'CT cured-at-12mo per 100 incident: {steps[-1]:.1f}')
    print(f'Saved {out}')

    # --- VDS presentation cascade (per 100 symptomatic women) ---
    vsteps, vlabels, vloss = vds_cascade_steps()
    fig, ax = pl.subplots(1, 1, figsize=(12, 5))
    plot_cascade(ax, vsteps, vlabels, vloss,
                 title='Vaginal discharge syndrome under syndromic management\nper 100 symptomatic women',
                 xlabel='per 100 symptomatic women')
    # overtreatment annotation on the treated bar (1b hook), flagged illustrative
    ax.text(vsteps[2] + 1.5, 0.0 + 0.0, '', fontsize=1)  # keep layout stable
    ax.annotate('most discharge is bacterial vaginosis, not an STI:\n'
                'much of this treatment is not for an STI (overtreatment)',
                xy=(vsteps[2], 0), xytext=(vsteps[2] + 22, 0.15),
                fontsize=12, color='#c0392b', style='italic',
                ha='left', va='center')
    fig.text(0.04, -0.03,
             'Per 100 women presenting with VDS. Seek care 0.49 and syndromic NG/CT '
             'routing 0.70 from model parameters. The correct-treatment vs overtreatment '
             'split requires the etiology mix of VDS presenters (ensemble). Preliminary: draw 773.',
             fontsize=11, color='#888888', ha='left')
    pl.tight_layout()
    out2 = f'{FIGURES_ARCHIVE}/fig_cascade_vds_soc.png'
    pl.savefig(out2, dpi=200, bbox_inches='tight')
    print(f'Saved {out2}')
