"""
Impact threshold plots from calibrated scenario sweeps.

For each sweep, compute scenario − baseline impact per posterior draw,
then plot median + 90% CI of the impact.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sciris as sc

OUTPUTS = Path(__file__).parent / 'outputs'
FIGURES = Path(__file__).parent / 'figures'

OUTCOME_LABELS = {
    'ng_inf': 'NG infections',
    'ct_inf': 'CT infections',
    'tv_inf': 'TV infections',
    'syph_inf': 'Syphilis infections',
    'hiv_inf': 'HIV infections',
    'syph_congenital': 'Congenital syphilis',
    'pn_notified': 'Partners notified',
    'pn_attending': 'Partners attending',
}


def compute_impacts(df):
    """Compute scenario − baseline for each draw."""
    baseline = df[df['scen'] == 'baseline'].set_index('draw_idx')
    outcome_cols = [c for c in df.columns if c not in
                    ['sweep', 'scen', 'draw_idx', 'ng_tx', 'ct_tx',
                     'lbw', 'sga', 'svn', 'births']]

    rows = []
    for _, row in df[df['scen'] != 'baseline'].iterrows():
        draw = row['draw_idx']
        if draw not in baseline.index:
            continue
        bl = baseline.loc[draw]
        impact = {}
        impact['sweep'] = row['sweep']
        impact['scen'] = row['scen']
        impact['draw_idx'] = draw
        for col in outcome_cols:
            if col in ('sweep', 'scen', 'draw_idx'):
                continue
            bl_val = bl[col] if col in bl.index else 0
            sc_val = row[col] if col in row.index else 0
            if pd.notna(bl_val) and pd.notna(sc_val):
                impact[f'{col}_averted'] = bl_val - sc_val  # positive = good
            else:
                impact[f'{col}_averted'] = np.nan
        rows.append(impact)

    return pd.DataFrame(rows)


def plot_pn_sweep(impacts):
    """PN coverage dose-response."""
    pn = impacts[impacts['sweep'] == 'pn_coverage'].copy()
    if len(pn) == 0:
        print('No PN coverage results')
        return

    scen_order = ['low', 'med', 'high']
    outcomes = ['ct_inf_averted', 'ng_inf_averted', 'tv_inf_averted',
                'syph_inf_averted', 'hiv_inf_averted']
    labels = ['CT', 'NG', 'TV', 'Syphilis', 'HIV']

    fig, axes = plt.subplots(1, len(outcomes), figsize=(4 * len(outcomes), 4),
                             sharey=False)

    for ax, col, label in zip(axes, outcomes, labels):
        medians = []
        lo = []
        hi = []
        for scen in scen_order:
            vals = pn[pn['scen'] == scen][col].dropna().values
            if len(vals) == 0:
                medians.append(0); lo.append(0); hi.append(0)
                continue
            medians.append(np.median(vals))
            lo.append(np.percentile(vals, 5))
            hi.append(np.percentile(vals, 95))

        x = np.arange(len(scen_order))
        medians = np.array(medians)
        lo = np.array(lo)
        hi = np.array(hi)

        ax.bar(x, medians, width=0.5, color='steelblue', alpha=0.7)
        ax.errorbar(x, medians, yerr=[medians - lo, hi - medians],
                    fmt='none', color='black', capsize=4)
        ax.axhline(0, color='grey', ls='--', lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(scen_order)
        ax.set_title(f'{label} averted', fontsize=11)
        ax.set_xlabel('PN coverage')
        ax.spines[['top', 'right']].set_visible(False)

    axes[0].set_ylabel('Infections averted (2020–2030)')
    fig.suptitle('Impact of partner notification coverage', fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'pn_impact.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "pn_impact.png"}')


def plot_care_seeking_sweep(impacts):
    """Care-seeking dose-response."""
    cs = impacts[impacts['sweep'] == 'care_seeking'].copy()
    if len(cs) == 0:
        print('No care-seeking results')
        return

    scen_order = ['cs_x1', 'cs_x1.25', 'cs_x1.5', 'cs_x2']
    scen_labels = ['1.0x', '1.25x', '1.5x', '2.0x']
    outcomes = ['ct_inf_averted', 'ng_inf_averted', 'tv_inf_averted']
    labels = ['CT', 'NG', 'TV']

    fig, axes = plt.subplots(1, len(outcomes), figsize=(4 * len(outcomes), 4),
                             sharey=False)

    for ax, col, label in zip(axes, outcomes, labels):
        medians = []
        lo = []
        hi = []
        for scen in scen_order:
            vals = cs[cs['scen'] == scen][col].dropna().values
            if len(vals) == 0:
                medians.append(0); lo.append(0); hi.append(0)
                continue
            medians.append(np.median(vals))
            lo.append(np.percentile(vals, 5))
            hi.append(np.percentile(vals, 95))

        x = np.arange(len(scen_order))
        medians = np.array(medians)
        lo = np.array(lo)
        hi = np.array(hi)

        ax.bar(x, medians, width=0.5, color='coral', alpha=0.7)
        ax.errorbar(x, medians, yerr=[medians - lo, hi - medians],
                    fmt='none', color='black', capsize=4)
        ax.axhline(0, color='grey', ls='--', lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(scen_labels)
        ax.set_title(f'{label} averted', fontsize=11)
        ax.set_xlabel('Care-seeking multiplier')
        ax.spines[['top', 'right']].set_visible(False)

    axes[0].set_ylabel('Infections averted (2020–2030)')
    fig.suptitle('Impact of increased care-seeking', fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'care_seeking_impact.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "care_seeking_impact.png"}')


def plot_summary_table(impacts):
    """Summary heatmap of median impacts across all sweeps."""
    outcomes = ['ng_inf_averted', 'ct_inf_averted', 'tv_inf_averted',
                'syph_inf_averted', 'hiv_inf_averted', 'syph_congenital_averted']
    labels = ['NG', 'CT', 'TV', 'Syphilis', 'HIV', 'Cong. syph']

    # All non-baseline scenarios
    scens = impacts['scen'].unique()
    scens = [s for s in scens if s != 'baseline']

    data = np.zeros((len(scens), len(outcomes)))
    for i, scen in enumerate(scens):
        for j, col in enumerate(outcomes):
            vals = impacts[impacts['scen'] == scen][col].dropna().values
            data[i, j] = np.median(vals) if len(vals) > 0 else 0

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(data, cmap='RdBu', aspect='auto',
                   vmin=-np.abs(data).max(), vmax=np.abs(data).max())
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_yticks(range(len(scens)))
    ax.set_yticklabels(scens, fontsize=9)

    # Annotate cells
    for i in range(len(scens)):
        for j in range(len(outcomes)):
            val = data[i, j]
            ax.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=8,
                    color='white' if abs(val) > np.abs(data).max() * 0.5 else 'black')

    plt.colorbar(im, ax=ax, label='Infections averted (positive = beneficial)')
    ax.set_title('Median infections averted by scenario (2020–2030)', fontsize=12)
    sc.figlayout()
    fig.savefig(FIGURES / 'impact_heatmap.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "impact_heatmap.png"}')


if __name__ == '__main__':
    FIGURES.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(OUTPUTS / 'scenario_results.csv')
    # Drop failed POC runs
    df = df.dropna(subset=['ng_inf'])
    print(f'Loaded {len(df)} results ({df["scen"].nunique()} scenarios)')

    impacts = compute_impacts(df)
    print(f'Computed {len(impacts)} impact rows')

    plot_pn_sweep(impacts)
    plot_care_seeking_sweep(impacts)
    plot_summary_table(impacts)
