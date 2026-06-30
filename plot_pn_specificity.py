"""POC specificity along the female->male (VDS) cascade + the PPV story.

POC diagnostics don't reduce prevalence/incidence, but they sharply improve the
SPECIFICITY of treatment and partner notification on the female (VDS) side.
'Over' is defined PERSON-LEVEL: a treated/notifying woman is over only if she
has NO STI at all (NG/CT/TV/syph; BV excluded) -- so a woman with a real STI who
gets a false-positive on a different pathogen, or who notifies her partner, is
NOT counted as over.

Panels (slide format, 12.15w x 5h):
  1. Female VDS treatment      person-level warranted vs over, SOC vs POC
  2. Female index notifies      notifications to male partners, warranted vs over
  3. PPV story                  residual POC over-treatment by pathogen vs
                                prevalence -- low-prevalence NG has poor PPV even
                                with 95%-specific tests.

Panels 1-2 from results/specificity.csv (diagnostics/specificity_tracer.py,
person-level, 5 seeds). Panel 3 from results/scenarios.kavg.csv (per-disease).

  conda run -n starsim python plot_pn_specificity.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
import matplotlib.patches as mpatches

REPO = Path(__file__).resolve().parent
SPEC = REPO / 'results' / 'specificity.csv'
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

WARRANT, OVER = '#3b86c4', '#e6772d'
SCALE = 8.7e6 / 1e4    # total_pop / n_agents -> people
YEARS = 2040 - 2027
POC = 'POC_c-baseline_p-baseline_b-none'


def set_font(size=12):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def main():
    set_font(12)
    s = pd.read_csv(SPEC)
    k = pd.read_csv(KAVG)
    x = np.arange(2)
    arms = ['SOC', 'POC']

    fig, axes = pl.subplots(1, 3, figsize=(12.15, 5))

    def stacked(ax, totals, overs, title, ylabel=None):
        """totals, overs: dict arm -> per-seed array (already scaled)."""
        tmax = 0
        for i, a in enumerate(arms):
            tot, ov = totals[a], overs[a]
            wm, om = np.median(tot - ov), np.median(ov)
            tmax = max(tmax, wm + om)
            ax.bar(i, wm, color=WARRANT, width=0.6, zorder=3)
            ax.bar(i, om, bottom=wm, color=OVER, width=0.6, zorder=3)
            pct = 100 * np.median(ov / np.where(tot > 0, tot, np.nan))
            ax.text(i, wm + om + 0.03 * max(tmax, 1e-9), f'{pct:.0f}%\nover',
                    ha='center', va='bottom', fontsize=11, color=OVER, linespacing=1.0)
        ax.set_xticks(x); ax.set_xticklabels(arms, fontsize=11)
        ax.set_ylim(0, tmax * 1.30); ax.set_xlim(-0.6, 1.6)
        ax.tick_params(axis='y', labelsize=9)
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_title(title, fontsize=13, pad=8)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)

    # ---- panel 1: female VDS treatment (person-level) ----
    f_tot = {a: s[s.arm == a].f_tx.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    f_ov = {a: s[s.arm == a].f_tx_over.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    stacked(axes[0], f_tot, f_ov, 'Female VDS treatment',
            ylabel='events / year (millions)')

    # ---- panel 2: notifications to male partners ----
    # notify rate is STI-agnostic, so split total notifications by the
    # person-level female-index over fraction (= f_tx_over / f_tx).
    n_tot, n_ov = {}, {}
    for a in arms:
        d = s[s.arm == a]
        notif = d.pn_notified_m.to_numpy(float) * SCALE / 1e6 / YEARS
        ofrac = d.f_tx_over.to_numpy(float) / d.f_tx.to_numpy(float)
        n_tot[a] = notif
        n_ov[a] = notif * ofrac
    stacked(axes[1], n_tot, n_ov, 'Female index notifies male partner')

    # ---- panel 3: PPV story (residual POC over by pathogen vs prevalence) ----
    ax = axes[2]
    dis = [('ng', 'NG'), ('tv', 'TV'), ('ct', 'CT')]  # ascending prevalence
    overs, prevs, labs = [], [], []
    for d, lab in dis:
        tx = np.median(k.loc[k.cell == POC, f'{d}_new_treated_f'])
        un = np.median(k.loc[k.cell == POC, f'{d}_new_treated_unnecessary_f'])
        pv = np.median(k.loc[k.cell == POC, f'{d}_prev_end'])
        overs.append(100 * un / tx); prevs.append(100 * pv); labs.append(lab)
    xb = np.arange(len(dis))
    ax.bar(xb, overs, color=OVER, width=0.6, zorder=3)
    for i, (o, p) in enumerate(zip(overs, prevs)):
        ax.text(i, o + 2, f'{o:.0f}%', ha='center', va='bottom', fontsize=11, color=OVER)
    ax.set_xticks(xb)
    ax.set_xticklabels([f'{l}\nprev {p:.0f}%' for l, p in zip(labs, prevs)], fontsize=10)
    ax.set_ylim(0, max(overs) * 1.25)
    ax.set_ylabel('% of POC treatments unnecessary', fontsize=11)
    ax.set_title('Residual over-treatment is a PPV effect', fontsize=13, pad=8)
    ax.tick_params(axis='y', labelsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    ax.text(0.97, 0.82, 'lower prevalence\n-> poorer PPV\n(at 95% specificity)',
            transform=ax.transAxes, fontsize=9, color='#666', ha='right', va='top')

    # cascade arrow between panels 1 and 2
    fig.text(0.355, 0.55, '→', ha='center', va='center', fontsize=22, color='#999')

    h = [mpatches.Patch(color=WARRANT), mpatches.Patch(color=OVER)]
    fig.legend(h, ['warranted (has an STI)', 'over (no STI at all)'], fontsize=10,
               frameon=False, loc='upper center', ncol=2, bbox_to_anchor=(0.5, 1.0))

    fig.text(0.5, 0.05,
             'Female-index VDS cascade. SOC vs POC-plain, draw 263 x 5 seeds, baseline PN fixed; person-level "over" = '
             'treated/notifying woman with no NG/CT/TV/syph infection (BV excluded). Bars = median annual events 2027-40.',
             ha='center', fontsize=8, color='#666666')
    fig.text(0.5, 0.02,
             'POC halves truly-unnecessary female treatment (48%->24%); the residual is concentrated in low-prevalence NG, '
             'where even a 95%-specific test has poor positive predictive value -- not a test failure.',
             ha='center', fontsize=8, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.985, top=0.9, bottom=0.16, wspace=0.28)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_pn_specificity.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
