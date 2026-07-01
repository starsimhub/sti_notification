"""Slide 6: POC diagnostics alone do not reduce prevalence or incidence.

Combines time-series plots with the endpoint bar comparison from
fig_poc_alone.py, in R1 colours (SOC gray, POC orange).

Layout (13 x 6.2):
  2 rows x 4 columns. Each cell has:
    * time-series (2027-2040) as the main panel showing prevalence
      (row 0) or new_infections / yr (row 1), SOC vs POC as two lines
      with 25-75 IQR bands
    * endpoint (2040) SOC vs POC bars as a small inset on the right of
      each TS panel

Also exposes `build_ts_grid_figure()` for slides 9-11, which reuse the
same 2x4 layout with additional arms layered in.

  conda run -n starsim python plot_slide6.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

REPO = Path(__file__).resolve().parent.parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
TS = REPO / 'results' / 'scenarios_timeseries.parquet'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

DISEASES = [('ng', 'Gonorrhoea'), ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'), ('syph', 'Syphilis')]
YEARS = 2040 - 2027
INTV = 2027


def med_iqr(vals):
    return np.median(vals), np.quantile(vals, 0.25), np.quantile(vals, 0.75)


def ts_slice(ts, cell, disease, result_name):
    """Return (years, per-draw values) for a single (cell, disease, metric)."""
    d = ts[(ts.cell == cell) & (ts.disease == disease)
           & (ts.result_name == result_name)]
    if len(d) == 0:
        return np.array([]), np.array([])
    piv = d.pivot_table(index='year', columns='draw', values='value',
                        aggfunc='first')
    return piv.index.to_numpy(), piv.to_numpy()  # (n_years, n_draws)


def draw_ts_panel(ax, ts, disease, result_name, arms, arm_c, scale=1.0, fs=10,
                  end_year=2040, band=True):
    """Time series for each arm in `arms`, median + optional 25-75 IQR band.

    arms: dict {label -> cell_name}
    arm_c: dict {label -> colour}
    end_year: trim to avoid artefactual drop at sim end (use 2039 for new_inf).
    band: whether to draw the IQR ribbon. Turn off when many arms overlap.
    """
    ymax = 0
    for arm_label, cell in arms.items():
        years, vals = ts_slice(ts, cell, disease, result_name)
        if len(years) == 0:
            continue
        v = vals * scale
        med = np.median(v, axis=1)
        q1 = np.quantile(v, 0.25, axis=1)
        q3 = np.quantile(v, 0.75, axis=1)
        mask = (years >= 2015) & (years <= end_year)
        cc = arm_c[arm_label]
        if band:
            ax.fill_between(years[mask], q1[mask], q3[mask], color=cc,
                            alpha=0.18, zorder=2, linewidth=0)
        ax.plot(years[mask], med[mask], color=cc, lw=1.6, zorder=3,
                label=arm_label)
        ymax = max(ymax, q3[mask].max() if band else med[mask].max())
    ax.axvline(INTV, color='#999', lw=0.8, ls='--', zorder=1)
    ax.set_xlim(2015, 2040)
    ax.set_ylim(0, ymax * 1.10 if ymax > 0 else 1)
    ax.tick_params(axis='both', labelsize=fs - 1)
    ax.spines[['top', 'right']].set_visible(False)


def draw_endpoint_bar(ax, k, disease, col, arms, arm_c,
                      is_scaled_millions=False, fs=9):
    """Endpoint bar chart with one bar per arm."""
    labels = list(arms)
    vals = {}
    for a in labels:
        raw = k.loc[k.cell == arms[a], col].to_numpy(float)
        if is_scaled_millions:
            raw = raw / 1e6 / YEARS
        vals[a] = raw
    ymax = max(np.median(vals[a]) for a in labels)
    for i, a in enumerate(labels):
        m, q1, q3 = med_iqr(vals[a])
        ax.bar(i, m, color=arm_c[a], width=0.75, zorder=3)
        ax.errorbar(i, m, yerr=[[m - q1], [q3 - m]], fmt='none',
                    ecolor='#555', elinewidth=0.6, capsize=1.6, zorder=4)
    ax.set_xticks(range(len(labels)))
    # Compact tick labels: use first letter of each arm, since we have arm
    # legend on the TS panel already
    if len(labels) <= 2:
        ax.set_xticklabels(labels, fontsize=fs - 2, rotation=0)
    else:
        # single-letter or digit tick labels
        ax.set_xticklabels(['S', 'P', '+L', '+M', '+H'][:len(labels)],
                           fontsize=fs - 2)
    ax.set_xlim(-0.55, len(labels) - 0.45)
    ax.set_ylim(0, ymax * 1.20)
    ax.tick_params(axis='y', labelsize=fs - 3)
    ax.spines[['top', 'right']].set_visible(False)


def build_ts_grid_figure(k, ts, arms, arm_c, suptitle,
                         caption_note=None, out_name='fig.png'):
    """2 rows x 4 disease columns, each cell = TS + endpoint bar.

    Row 0: prevalence.  Row 1: new_infections/yr (trimmed to 2039).
    """
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    # Subset the timeseries to only the arms we plot -- keeps memory + IO down
    ts_sub = ts[ts.cell.isin(arms.values())]

    fig = pl.figure(figsize=(13, 6.4))
    outer = GridSpec(2, 4, figure=fig, left=0.065, right=0.985,
                     top=0.82, bottom=0.10, hspace=0.42, wspace=0.32)

    for c, (d, dname) in enumerate(DISEASES):
        # Row 0: prevalence
        inner_p = GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[0, c],
                                          width_ratios=[3.4, 1.2], wspace=0.35)
        ax_ts = fig.add_subplot(inner_p[0])
        ax_bar = fig.add_subplot(inner_p[1])
        draw_ts_panel(ax_ts, ts_sub, d, 'prevalence', arms, arm_c)
        draw_endpoint_bar(ax_bar, k, d, f'{d}_prev_end', arms, arm_c,
                          is_scaled_millions=False)
        ax_ts.set_title(dname, fontsize=12.5, pad=6)
        ax_bar.set_title('2040', fontsize=9, pad=3, color='#666')
        if c == 0:
            ax_ts.set_ylabel('prevalence', fontsize=10.5)
            ax_ts.legend(fontsize=8.5, frameon=False, loc='upper left',
                         labelspacing=0.15, handlelength=1.4)

        # Row 1: incidence (trimmed to 2039 to avoid end-year artefact)
        inner_i = GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[1, c],
                                          width_ratios=[3.4, 1.2], wspace=0.35)
        ax_ts = fig.add_subplot(inner_i[0])
        ax_bar = fig.add_subplot(inner_i[1])
        draw_ts_panel(ax_ts, ts_sub, d, 'new_infections', arms, arm_c,
                      scale=1 / 1e6, end_year=2039)
        draw_endpoint_bar(ax_bar, k, d, f'{d}_new_inf', arms, arm_c,
                          is_scaled_millions=True)
        ax_bar.set_title('cum. 27–40', fontsize=9, pad=3, color='#666')
        if c == 0:
            ax_ts.set_ylabel('new infections / yr (M)', fontsize=10.5)

    fig.suptitle(suptitle, fontsize=12.5, y=0.965)
    caption = ('Ensemble of 5 calibrated draws (exp 06 top-5). '
               'Lines = median across draws; bands = 25–75 IQR. '
               'Vertical dashed line = intervention start (2027).')
    if caption_note:
        caption = caption + ' ' + caption_note
    fig.text(0.5, 0.02, caption, ha='center', fontsize=8.5, color='#666666')

    FIGS.mkdir(exist_ok=True)
    p = FIGS / out_name
    fig.savefig(p, dpi=200)
    print('wrote', p)
    return p


def main():
    ARMS = {'SOC': 'SOC', 'POC': 'POC_c-baseline_p-baseline_b-none'}
    ARM_C = {'SOC': '#555555', 'POC': '#e6772d'}
    k = pd.read_csv(KAVG)
    ts = pd.read_parquet(TS)
    build_ts_grid_figure(
        k, ts, ARMS, ARM_C,
        suptitle=('POC diagnostics alone do not reduce prevalence or '
                  'incidence — trajectories continue upward under both arms'),
        out_name='fig_slide6.png',
    )


if __name__ == '__main__':
    main()
