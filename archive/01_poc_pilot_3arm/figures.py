"""Figures for exp 01 — POC × PN × FSW outreach × care-seeking pilot.

Reads outputs/results.jsonl (one row per arm × draw × seed) and writes
four PNGs into figures/. Run as `python figures.py` from the project
root (same as analyze.py).

Figures:
  1. fig1_prevalent_cases_reduction.png — bar chart per disease, per
     arm, showing % reduction in n_infected at 2040 vs the A baseline.
     Mean across draws+seeds, error bars = 95% CI of the mean.
  2. fig2_treatment_rate_3_6mo.png — grouped bars per disease showing
     the 3-month and 6-month per-episode treatment rates, by arm.
  3. fig3_pn_cascade.png — per-arm horizontal stacked bars showing the
     PN cascade: indices → notified → attending → attending with no STI.
  4. fig4_care_seeking_threshold.png — care-seeking multiplier on the
     x-axis (1×, 1.5×, 2×, 3× from D, E1, E2, E3), per-disease lines
     for prevalent-cases reduction. Labelled as a thresholding analysis
     pending the proper care-seeking sweep (separate experiment).

All figures are draw+seed-averaged. Where error bars are shown they
use a normal-theory 95% CI of the mean across draws (n=30 per arm).
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs'
FIG = HERE / 'figures'
RESULTS = OUT / 'results.jsonl'

ARM_ORDER = ['A_soc', 'B_poc_baseline', 'C1_poc_pn_1_5x',
             'C2_poc_pn_2x', 'C3_poc_pn_3x', 'D_poc_pn_3x_fsw_out',
             'E1_d_careseek_1_5x', 'E2_d_careseek_2x', 'E3_d_careseek_3x']
ARM_SHORT = {
    'A_soc':               'A',
    'B_poc_baseline':      'B',
    'C1_poc_pn_1_5x':      'C1',
    'C2_poc_pn_2x':        'C2',
    'C3_poc_pn_3x':        'C3',
    'D_poc_pn_3x_fsw_out': 'D',
    'E1_d_careseek_1_5x':  'E1',
    'E2_d_careseek_2x':    'E2',
    'E3_d_careseek_3x':    'E3',
}

# Diseases shown in the per-disease figures. BV is excluded — it's at
# equilibrium across arms and not the policy target.
DISEASES = ['ng', 'ct', 'tv', 'syph']
DISEASE_LABEL = {'ng': 'Gonorrhoea', 'ct': 'Chlamydia',
                 'tv': 'Trichomoniasis', 'syph': 'Syphilis'}

# Colour assignment by intervention family (consistent across figures).
ARM_COLOR = {
    'A':  '#444444',  # SOC baseline = dark grey
    'B':  '#1f77b4',  # POC baseline = blue
    'C1': '#7baad7',  'C2': '#5494c8', 'C3': '#2f78b8',  # POC × PN
    'D':  '#2ca02c',  # POC × PN × FSW = green
    'E1': '#f4a261',  'E2': '#e76f51', 'E3': '#bc4749',  # care-seeking
}


def load_results():
    rows = []
    with RESULTS.open() as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
    df = pd.DataFrame(rows)
    if 'status' in df.columns:
        df = df[df['status'] == 'ok'].copy()
    return df


def arm_mean_ci(df, col):
    """Return dict {arm: (mean, half_width_95)} across draw+seed."""
    out = {}
    for arm in ARM_ORDER:
        sub = df.loc[df['arm'] == arm, col].astype(float).dropna()
        if len(sub) == 0:
            out[arm] = (np.nan, np.nan)
            continue
        m = sub.mean()
        sem = sub.std(ddof=1) / np.sqrt(len(sub)) if len(sub) > 1 else 0.0
        out[arm] = (m, 1.96 * sem)
    return out


def fig1_prevalent_cases_reduction(df, path):
    """Bar chart: % reduction in n_infected at 2040 vs A, per disease per arm.

    Negative bars = reduction. Arm A is the reference (0 by construction).
    """
    fig, ax = plt.subplots(figsize=(11, 5.5))
    n_arms = len(ARM_ORDER)
    n_dis = len(DISEASES)
    bar_w = 0.8 / n_arms

    # For each disease, compute (% reduction vs A) per arm.
    for di, d in enumerate(DISEASES):
        ni_by_arm = arm_mean_ci(df, f'{d}_n_infected_end')
        ref_mean = ni_by_arm['A_soc'][0]
        if not np.isfinite(ref_mean) or ref_mean == 0:
            continue
        for ai, arm in enumerate(ARM_ORDER):
            m, hw = ni_by_arm[arm]
            if not np.isfinite(m):
                continue
            pct = 100.0 * (m - ref_mean) / ref_mean
            # CI half-width in percent (treat as proportional to mean's CI)
            hw_pct = 100.0 * hw / ref_mean if np.isfinite(hw) else 0
            x = di + (ai - (n_arms - 1) / 2) * bar_w
            ax.bar(x, pct, width=bar_w,
                   color=ARM_COLOR[ARM_SHORT[arm]],
                   edgecolor='none',
                   yerr=hw_pct if arm != 'A_soc' else 0,
                   capsize=2,
                   error_kw={'elinewidth': 0.7, 'ecolor': '#666'})

    ax.axhline(0, color='black', lw=0.8)
    ax.set_xticks(range(n_dis))
    ax.set_xticklabels([DISEASE_LABEL[d] for d in DISEASES])
    ax.set_ylabel('% change in prevalent cases at 2040 vs SOC (arm A)')
    ax.set_title('Reduction in prevalent infections at 2040, by arm and disease')
    ax.grid(axis='y', alpha=0.3)

    legend_handles = [Patch(facecolor=ARM_COLOR[ARM_SHORT[a]],
                            label=ARM_SHORT[a]) for a in ARM_ORDER]
    ax.legend(handles=legend_handles, ncol=n_arms,
              loc='upper center', bbox_to_anchor=(0.5, -0.10),
              fontsize=9, frameon=False)

    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'Wrote {path}')


def fig2_treatment_rate_3_6mo(df, path):
    """Grouped bars per disease showing 3-mo and 6-mo per-episode
    treatment rates by arm. Two sub-bars per arm: 3-mo (darker) and
    6-mo (lighter, on top)."""
    fig, axes = plt.subplots(1, len(DISEASES), figsize=(14, 4.5),
                             sharey=True)
    for ax, d in zip(axes, DISEASES):
        rates_3 = arm_mean_ci(df, f'{d}_prop_treated_3mo')
        rates_6 = arm_mean_ci(df, f'{d}_prop_treated_6mo')
        x = np.arange(len(ARM_ORDER))
        m3 = [rates_3[a][0] * 100 for a in ARM_ORDER]
        m6 = [rates_6[a][0] * 100 for a in ARM_ORDER]
        e3 = [rates_3[a][1] * 100 for a in ARM_ORDER]
        e6 = [rates_6[a][1] * 100 for a in ARM_ORDER]
        colors = [ARM_COLOR[ARM_SHORT[a]] for a in ARM_ORDER]
        ax.bar(x - 0.2, m3, width=0.38, color=colors,
               yerr=e3, capsize=2,
               edgecolor='#222', linewidth=0.4,
               error_kw={'elinewidth': 0.6, 'ecolor': '#444'},
               label='3-month')
        ax.bar(x + 0.2, m6, width=0.38, color=colors, alpha=0.55,
               yerr=e6, capsize=2,
               edgecolor='#222', linewidth=0.4,
               error_kw={'elinewidth': 0.6, 'ecolor': '#444'},
               label='6-month')
        ax.set_xticks(x)
        ax.set_xticklabels([ARM_SHORT[a] for a in ARM_ORDER],
                           rotation=0, fontsize=8)
        ax.set_title(DISEASE_LABEL[d])
        ax.grid(axis='y', alpha=0.3)
        if ax is axes[0]:
            ax.set_ylabel('Per-episode treatment rate (%)')

    # Legend explaining the 3mo vs 6mo bars (uses arm A's colour for clarity)
    ref = ARM_COLOR['A']
    handles = [
        Patch(facecolor=ref, label='3 months of acquisition'),
        Patch(facecolor=ref, alpha=0.55, label='6 months of acquisition'),
    ]
    axes[-1].legend(handles=handles, loc='upper left', fontsize=9,
                    frameon=False, title='Treated within…')

    fig.suptitle('Per-episode treatment rate within 3 / 6 months of acquisition, by arm',
                 y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'Wrote {path}')


def fig3_pn_cascade(df, path):
    """Horizontal cascade bars per arm: indices over-treated (no STI),
    PN partners notified, attending, attending with no STI."""
    cols = [
        ('pn_index_no_sti_2027_2040',     'Indices over-treated\n(no STI at moment of treatment)'),
        ('pn_notified_2027_2040',         'Partners notified'),
        ('pn_attending_2027_2040',        'Partners attending'),
        ('pn_attended_no_sti_2027_2040',  'Attendees with no STI found'),
    ]
    n_arms = len(ARM_ORDER)
    fig, ax = plt.subplots(figsize=(11, 6.5))
    bar_h = 0.18
    for ci, (col, _) in enumerate(cols):
        means = arm_mean_ci(df, col)
        ys = np.arange(n_arms) + (ci - (len(cols) - 1) / 2) * bar_h
        vals = [means[a][0] / 1e6 for a in ARM_ORDER]
        errs = [means[a][1] / 1e6 for a in ARM_ORDER]
        colors = [ARM_COLOR[ARM_SHORT[a]] for a in ARM_ORDER]
        # Lower alpha for the "wasted" rows so the cascade is readable
        alpha = 1.0 if ci in (1, 2) else 0.7
        ax.barh(ys, vals, height=bar_h, color=colors, alpha=alpha,
                edgecolor='#222', linewidth=0.4,
                xerr=errs, error_kw={'elinewidth': 0.6, 'ecolor': '#444'})

    ax.set_yticks(np.arange(n_arms))
    ax.set_yticklabels([ARM_SHORT[a] for a in ARM_ORDER])
    ax.invert_yaxis()
    ax.set_xlabel('Millions of agents (Zimbabwe-scaled, 2027–2040)')
    ax.set_title('PN cascade by arm')
    ax.grid(axis='x', alpha=0.3)

    # Stage legend (uses arm-A colour as exemplar)
    ref = ARM_COLOR['A']
    handles = [Patch(facecolor=ref, alpha=0.7 if i in (0, 3) else 1.0,
                     label=label)
               for i, (_, label) in enumerate(cols)]
    ax.legend(handles=handles, loc='lower right', fontsize=8,
              frameon=False, title='Cascade stage (top → bottom within each arm)')

    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'Wrote {path}')


def fig4_care_seeking_threshold(df, path):
    """Threshold-style line chart: % reduction in prevalent cases vs
    care-seeking multiplier (1×, 1.5×, 2×, 3× from D, E1, E2, E3).

    All four lines start at D (1×) which is "everything currently
    feasible" — POC + 3× PN + FSW outreach + no care-seeking change.
    Labelled as a thresholding analysis pending the proper sweep.
    """
    mults = [1.0, 1.5, 2.0, 3.0]
    mult_arms = ['D_poc_pn_3x_fsw_out', 'E1_d_careseek_1_5x',
                 'E2_d_careseek_2x', 'E3_d_careseek_3x']
    fig, ax = plt.subplots(figsize=(8, 5.5))
    for d in DISEASES:
        ref_mean = arm_mean_ci(df, f'{d}_n_infected_end')['A_soc'][0]
        if not np.isfinite(ref_mean) or ref_mean == 0:
            continue
        ys, errs = [], []
        for arm in mult_arms:
            m, hw = arm_mean_ci(df, f'{d}_n_infected_end')[arm]
            ys.append(100.0 * (m - ref_mean) / ref_mean if np.isfinite(m) else np.nan)
            errs.append(100.0 * hw / ref_mean if np.isfinite(hw) else 0)
        ax.errorbar(mults, ys, yerr=errs, marker='o',
                    label=DISEASE_LABEL[d], capsize=3, lw=2)

    ax.axhline(0, color='black', lw=0.8)
    ax.set_xticks(mults)
    ax.set_xticklabels([f'{m:g}×' for m in mults])
    ax.set_xlabel('Symptomatic care-seeking multiplier (over D-arm baseline)')
    ax.set_ylabel('% change in prevalent cases at 2040 vs SOC (arm A)')
    ax.set_title('Thresholding analysis: prevalent-case reduction by care-seeking lever\n'
                 '(pending proper sweep — current data: D, E1, E2, E3)')
    ax.grid(alpha=0.3)
    ax.legend(loc='lower left', frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)
    print(f'Wrote {path}')


def main():
    if not RESULTS.exists():
        raise SystemExit(f'No {RESULTS}; run run.py first.')
    FIG.mkdir(parents=True, exist_ok=True)
    df = load_results()
    print(f'Loaded {len(df)} rows; arms: {sorted(df["arm"].unique())}')
    fig1_prevalent_cases_reduction(df, FIG / 'fig1_prevalent_cases_reduction.png')
    fig2_treatment_rate_3_6mo(df, FIG / 'fig2_treatment_rate_3_6mo.png')
    fig3_pn_cascade(df, FIG / 'fig3_pn_cascade.png')
    fig4_care_seeking_threshold(df, FIG / 'fig4_care_seeking_threshold.png')


if __name__ == '__main__':
    main()
