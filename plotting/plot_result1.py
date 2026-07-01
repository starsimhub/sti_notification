"""Result 1: POC diagnostics sharply improve treatment specificity but cannot eliminate overtreatment.

Layout: 9.7 x 5 inches, 2 columns.
  Left  — 6 mini-panels (2 cols x 3 rows)
    rows 0-1: treatment precision for NG / CT / TV / Syph (poc_alone style)
    row  2:   female VDS treatment (pn_specificity style); female GUD treatment
  Right — VDS etiology upset plot (explains residual overtreatment)

  conda run -n starsim python plot_result1.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

REPO = Path(__file__).resolve().parent.parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
SPEC = REPO / 'results' / 'specificity.csv'
VDS_CSV = REPO / 'results' / 'vds_etiology.csv'
FIGS = REPO / 'figures'
FONT = str(REPO / 'assets' / 'LibertinusSans-Regular.otf')

DARK, UDOT = '#2c3e50', '#d7dbe0'

ARMS = {'SOC': 'SOC', 'POC': 'POC_c-baseline_p-baseline_b-none'}
ARM_C = {'SOC': '#555555', 'POC': '#e6772d'}
DISEASES = [('ng', 'Gonorrhoea'), ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'), ('syph', 'Syphilis')]
YEARS = 2040 - 2027
SCALE = 8.7e6 / 1e4

VDS_PATHS = ['ng', 'ct', 'tv', 'bv']
VDS_NAMES = {'ng': 'NG', 'ct': 'CT', 'tv': 'TV', 'bv': 'BV'}
COMBOS = ['ng_only', 'ct_only', 'tv_only', 'bv_only', 'ng_ct', 'ng_tv', 'ng_bv',
          'ct_tv', 'ct_bv', 'tv_bv', 'ng_ct_tv', 'ng_ct_bv', 'ng_tv_bv',
          'ct_tv_bv', 'ng_ct_tv_bv']


def members(combo):
    return [t for t in combo.split('_') if t in VDS_PATHS]


def med_iqr(vals):
    return np.median(vals), np.quantile(vals, 0.25), np.quantile(vals, 0.75)


def kavg(k, cell, col):
    return k.loc[k.cell == cell, col].to_numpy(dtype=float)


def precision_panel(ax, k, disease, fs=10):
    """Appropriate vs unnecessary treatment, SOC vs POC (poc_alone style)."""
    arms = list(ARMS)
    tot = {a: kavg(k, ARMS[a], f'{disease}_new_treated') / 1e6 / YEARS for a in arms}
    un  = {a: kavg(k, ARMS[a], f'{disease}_new_treated_unnecessary') / 1e6 / YEARS for a in arms}
    app = {a: tot[a] - un[a] for a in arms}
    unct = {a: 100 * np.median(un[a] / np.where(tot[a] > 0, tot[a], np.nan)) for a in arms}
    tmax = max(np.median(tot[a]) for a in arms)
    for i, a in enumerate(arms):
        cc = ARM_C[a]
        am, um = np.median(app[a]), np.median(un[a])
        ax.bar(i, am, color=cc, width=0.6, zorder=3)
        ax.bar(i, um, bottom=am, color=cc, alpha=0.28, width=0.6, zorder=3)
        ax.text(i, am + um + tmax * 0.05, f'{unct[a]:.0f}%\nover', ha='center',
                va='bottom', fontsize=fs - 0.5, color=cc, linespacing=1.0)
    ax.set_xlim(-0.6, 1.6); ax.set_ylim(bottom=0); ax.margins(y=0.60)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['SOC', 'POC'], fontsize=fs - 1)
    ax.tick_params(axis='y', labelsize=fs - 1)
    ax.spines[['top', 'right']].set_visible(False)


def specificity_panel(ax, tot_d, ov_d, fs=10):
    """Warranted vs over treatment, SOC vs POC (pn_specificity style)."""
    arms = ['SOC', 'POC']
    tmax = max(np.median(tot_d[a]) for a in arms)
    for i, a in enumerate(arms):
        tot, ov = tot_d[a], ov_d[a]
        wm, om = np.median(tot - ov), np.median(ov)
        tm, q1, q3 = med_iqr(tot)
        cc = ARM_C[a]
        ax.bar(i, wm, color=cc, width=0.6, zorder=3)
        ax.bar(i, om, bottom=wm, color=cc, alpha=0.28, width=0.6, zorder=3)
        ax.errorbar(i, tm, yerr=[[tm - q1], [q3 - tm]], fmt='none',
                    ecolor='#555', elinewidth=0.8, capsize=2, zorder=4)
        pct = 100 * np.median(ov / np.where(tot > 0, tot, np.nan))
        ax.text(i, np.median(tot) + tmax * 0.12, f'{pct:.0f}%\nover',
                ha='center', va='bottom', fontsize=fs - 0.5, color=cc, linespacing=1.0)
    ax.set_xlim(-0.6, 1.6); ax.set_xticks([0, 1])
    ax.set_xticklabels(arms, fontsize=fs - 1)
    ax.set_ylim(0, tmax * 1.55)
    ax.tick_params(axis='y', labelsize=fs - 1)
    ax.spines[['top', 'right']].set_visible(False)


def upset_panels(ax_bar, ax_mat, ax_set, marg, combo, vds_prev, fs=10):
    """Upset plot drawn into three provided axes."""
    rows = sorted(VDS_PATHS, key=lambda p: marg[p])
    cols = [c for c in sorted(COMBOS, key=lambda c: combo[c], reverse=True) if combo[c] > 0]
    n = len(cols)
    x = np.arange(n)
    vals = [combo[c] * 100 for c in cols]

    ax_bar.bar(x, vals, color='#4a90d9', width=0.55)
    for xi, v in zip(x, vals):
        if v >= 2:
            ax_bar.text(xi, v + max(vals) * 0.05, f'{v:.0f}',
                        ha='center', fontsize=fs - 3, color=DARK)
    ax_bar.set_ylabel('% of VDS women', fontsize=fs - 1)
    ax_bar.set_ylim(0, max(vals) * 1.18)
    ax_bar.spines[['top', 'right']].set_visible(False)
    ax_bar.tick_params(labelbottom=False, labelsize=fs - 2)

    yrow = {p: i for i, p in enumerate(rows)}
    for j, c in enumerate(cols):
        present = members(c)
        ax_mat.scatter([j] * len(rows), range(len(rows)),
                       c=[DARK if p in present else UDOT for p in rows], s=30, zorder=2)
        idx = sorted(yrow[p] for p in present)
        if len(idx) > 1:
            ax_mat.plot([j, j], [idx[0], idx[-1]], color=DARK, lw=1.5, zorder=1)
    ax_mat.set_yticks(range(len(rows)))
    ax_mat.set_yticklabels([VDS_NAMES[p] for p in rows], fontsize=fs)
    ax_mat.set_ylim(-0.6, len(rows) - 0.4)
    ax_mat.set_xlim(-0.6, n - 0.4)
    ax_mat.tick_params(labelbottom=False, length=0)
    ax_mat.spines[['top', 'right', 'bottom', 'left']].set_visible(False)

    ax_set.barh(range(len(rows)), [marg[p] * 100 for p in rows], color='#9aa0a6', height=0.5)
    for i, p in enumerate(rows):
        ax_set.text(marg[p] * 100 + 3, i, f'{marg[p]:.0%}', va='center',
                    ha='right', fontsize=fs - 2.5, color=DARK)
    ax_set.invert_xaxis()
    ax_set.set_xlabel('carriage (%)', fontsize=fs - 1)
    ax_set.tick_params(labelleft=False, length=0, labelsize=fs - 2)
    ax_set.spines[['top', 'right', 'left']].set_visible(False)
    ax_set.set_xlim(max(marg.values()) * 100 * 1.80, 0)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    k = pd.read_csv(KAVG)
    s = pd.read_csv(SPEC)
    vd = dict(zip(*[pd.read_csv(VDS_CSV)[c] for c in ('metric', 'value')]))
    vds_prev = vd['vds_prev']
    marg  = {p: vd[f'marg_{p}'] for p in VDS_PATHS}
    combo = {c: vd[c] for c in COMBOS}

    # ---- Figure layout -------------------------------------------------------
    fig = pl.figure(figsize=(9.7, 5))
    outer = GridSpec(1, 2, figure=fig, width_ratios=[5.4, 4.3],
                     left=0.05, right=0.995, top=0.91, bottom=0.10, wspace=0.18)
    left_gs  = GridSpecFromSubplotSpec(3, 2, subplot_spec=outer[0],
                                       hspace=0.60, wspace=0.42)
    right_gs = GridSpecFromSubplotSpec(2, 2, subplot_spec=outer[1],
                                       width_ratios=[0.85, 5], height_ratios=[2.6, 1.5],
                                       hspace=0.08, wspace=0.18)

    # ---- Left: rows 0-1, treatment precision (4 disease panels) -------------
    for idx, (d_key, d_name) in enumerate(DISEASES):
        r, c = divmod(idx, 2)
        ax = fig.add_subplot(left_gs[r, c])
        precision_panel(ax, k, d_key)
        ax.set_title(d_name, fontsize=10.5, pad=3)
        if c == 0:
            ax.set_ylabel('tx / yr (M)', fontsize=9, labelpad=2)
        if r == 0:
            ax.set_ylim(top=2)
        if r == 1:
            ax.set_ylim(top=1)

    # ---- Left: row 2, female VDS treatment -----------------------------------
    ax_vds = fig.add_subplot(left_gs[2, 0])
    arms = ['SOC', 'POC']
    f_tot = {a: s[s.arm == a].f_tx.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    f_ov  = {a: s[s.arm == a].f_tx_over.to_numpy(float) * SCALE / 1e6 / YEARS for a in arms}
    specificity_panel(ax_vds, f_tot, f_ov)
    ax_vds.set_title('Female VDS treatment', fontsize=10.5, pad=3)
    ax_vds.set_ylabel('events / yr (M)', fontsize=9, labelpad=2)

    # ---- Left: row 2, female GUD treatment -----------------------------------
    ax_gud = fig.add_subplot(left_gs[2, 1])
    POC_CELL = ARMS['POC']
    g_tot = {
        'SOC': k[k.cell == 'SOC'][   'syph_new_treated_f'].to_numpy(float) / 1e6 / YEARS,
        'POC': k[k.cell == POC_CELL]['syph_new_treated_f'].to_numpy(float) / 1e6 / YEARS,
    }
    g_ov = {
        'SOC': k[k.cell == 'SOC'][   'syph_new_treated_unnecessary_f'].to_numpy(float) / 1e6 / YEARS,
        'POC': k[k.cell == POC_CELL]['syph_new_treated_unnecessary_f'].to_numpy(float) / 1e6 / YEARS,
    }
    specificity_panel(ax_gud, g_tot, g_ov)
    ax_gud.set_title('Female GUD treatment', fontsize=10.5, pad=3)

    # ---- Legend --------------------------------------------------------------
    h = [mpatches.Patch(facecolor='#888', edgecolor='none'),
         mpatches.Patch(facecolor='#888', alpha=0.28, edgecolor='none')]
    fig.legend(h, ['warranted', 'unnecessary'], fontsize=9, frameon=False,
               loc='upper left', bbox_to_anchor=(0.05, 1.01), ncol=2,
               handlelength=1.0, handletextpad=0.4)

    # ---- Right: upset --------------------------------------------------------
    ax_bar = fig.add_subplot(right_gs[0, 1])
    ax_mat = fig.add_subplot(right_gs[1, 1], sharex=ax_bar)
    ax_set = fig.add_subplot(right_gs[1, 0], sharey=ax_mat)
    upset_panels(ax_bar, ax_mat, ax_set, marg, combo, vds_prev)
    ax_bar.set_title('VDS etiology (2030–40)', fontsize=10.5, pad=3)

    # fig.text(0.5, 0.02,
    #          f'Left: kavg 5 draws (exp 06), baseline PN, bars = median, whiskers = 25–75 IQR. '
    #          f'VDS/GUD person-level: over = treated with no NG/CT/TV/syph. '
    #          f'Right: draw 68, VDS prev {vds_prev:.0%}.',
    #          ha='center', fontsize=8, color='#666666')

    # Superseded by plot_slide5 (grid) + plot_slide4_etiology (upset) for the
    # deck; the standalone figure lives in figures/archive/.
    out_dir = FIGS / 'archive'
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / 'fig_result1.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
