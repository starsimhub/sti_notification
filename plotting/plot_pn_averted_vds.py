"""Impact of a POC CT/NG/TV test on partner notification of women with VDS,
Zimbabwe (model) and South Africa (illustrative). For R. Peters, WHO STI dept.

Per 100 VDS presenters, decomposes male-partner notifications into warranted
(index actually has NG/CT/TV) vs unnecessary (false positive on panel, or
BV/other with no STI). The POC bar reflects the 3-test VDS panel (NG + CT + TV)
at per-pathogen sens/spec from this project's dx table. A truly STI-negative
woman still triggers PN with probability 1 - 0.95^3 ~ 14%.

    conda run -n starsim python plotting/plot_pn_averted_vds.py
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
from matplotlib.gridspec import GridSpec

REPO = Path(__file__).resolve().parent.parent
VDS_CSV = REPO / 'results' / 'vds_etiology.csv'
FIGS = REPO / 'figures'
FONT = str(REPO / 'assets' / 'LibertinusSans-Regular.otf')

ARM_C = {'SOC': '#555555', 'POC': '#e6772d'}

POC_SPEC = 0.95  # per pathogen, applied across 3 VDS tests (NG + CT + TV)
POC_SENS = 0.95  # average detection for a truly STI+ VDS presenter

# Peters (WHO STI dept, pers. comm.); consistent with SA VDS aetiology
# surveillance. No modelled uncertainty around this value.
SA_ANY_STI = 0.30


def read_zim_etiology():
    d = dict(zip(*pd.read_csv(VDS_CSV).to_dict('list').values()))
    no_sti = d['bv_only']        # VDS trigger = any NG/CT/TV/BV symptom; BV-only
    return 1 - no_sti, no_sti    # is the only bucket with no NG/CT/TV


def compound_fp(spec=POC_SPEC, n=3):
    return 1 - spec ** n


def arm_decomp(any_sti, no_sti, arm):
    if arm == 'SOC':
        return 100 * any_sti, 100 * no_sti
    return 100 * any_sti * POC_SENS, 100 * no_sti * compound_fp()


def country_panel(ax, title, source, any_sti, no_sti, fs=11):
    arms = ['SOC', 'POC']
    totals, unnecs = {}, {}
    for i, a in enumerate(arms):
        warr, unnec = arm_decomp(any_sti, no_sti, a)
        totals[a] = warr + unnec
        unnecs[a] = unnec
        cc = ARM_C[a]
        ax.bar(i, warr, color=cc, width=0.55, zorder=3)
        ax.bar(i, unnec, bottom=warr, color=cc, alpha=0.28, width=0.55, zorder=3)
        total = warr + unnec
        unnec_pct = 100 * unnec / total if total else 0
        ax.text(i, total + 3, f'{total:.0f}', ha='center', va='bottom',
                fontsize=fs, color=cc, weight='bold')
        if unnec > 4:
            ax.text(i, warr + unnec / 2, f'{unnec_pct:.0f}%\nunnecessary',
                    ha='center', va='center', fontsize=fs - 2, color=cc,
                    linespacing=1.0)
    red_total = 100 * (1 - totals['POC'] / totals['SOC'])
    red_unnec = 100 * (1 - unnecs['POC'] / unnecs['SOC'])
    ax.annotate('', xy=(1, totals['POC'] + 10),
                xytext=(0, totals['SOC'] + 10),
                arrowprops=dict(arrowstyle='->', color=ARM_C['POC'], lw=1.4))
    ax.text(0.5, max(totals.values()) + 18,
            f'−{red_total:.0f}% notifications overall\n'
            f'−{red_unnec:.0f}% unnecessary',
            ha='center', va='bottom', fontsize=fs, color=ARM_C['POC'],
            weight='bold', linespacing=1.2)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(arms, fontsize=fs)
    ax.set_ylim(0, 135)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel('male-partner notifications\nper 100 women with VDS',
                  fontsize=fs - 1)
    ax.set_title(title, fontsize=fs + 1, pad=6)
    ax.text(0.5, -0.17, source, transform=ax.transAxes, ha='center',
            fontsize=fs - 2, style='italic', color='#666', linespacing=1.2)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(labelsize=fs - 2)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    zim_any, zim_no = read_zim_etiology()
    sa_any, sa_no = SA_ANY_STI, 1 - SA_ANY_STI

    fig = pl.figure(figsize=(8.5, 5.4))
    gs = GridSpec(1, 2, figure=fig, left=0.10, right=0.985, top=0.84,
                  bottom=0.18, wspace=0.42)

    country_panel(fig.add_subplot(gs[0]), 'Zimbabwe',
                  f'{zim_any*100:.0f}% of women presenting with VDS have NG, CT, or TV\n'
                  '(model, calibration ensemble)',
                  zim_any, zim_no)
    country_panel(fig.add_subplot(gs[1]), 'South Africa (illustrative)',
                  f'~{sa_any*100:.0f}% of women presenting with VDS have NG, CT, or TV',
                  sa_any, sa_no)

    FIGS.mkdir(exist_ok=True)
    out = FIGS / 'fig_pn_averted_vds.png'
    fig.savefig(out, dpi=200)
    print('wrote', out)


if __name__ == '__main__':
    main()
