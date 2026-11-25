"""Headline numbers for the manuscript ([XX] values in docs/sti_manuscript_v3.md).

Reads results/scenarios.kavg.csv (via analysis/fp_harms.load) and results/shapley.csv, and writes
results/headlines.md: each number as the median (IQR) across parameter sets, with the scenario it comes from.

    python analysis/headlines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fp_harms  # noqa: E402
from scenarios import BASE_SPEC, SPEC_SWEEP  # noqa: E402

RES = fp_harms.RES
YEARS = 2040 - 2027 + 1


def cell(d, care, pn, bp, spec=BASE_SPEC):
    """ The per-draw rows of one POC cell """
    m = d.poc & (d.care == care) & (d.pn == pn) & (d.bp == bp) & np.isclose(d.spec.astype(float), spec)
    return d[m]


def fmt(s, pct=False, sig=3):
    s = pd.Series(s).dropna()
    f = (lambda v: f'{100*v:.1f}%') if pct else (lambda v: f'{v:.{sig}g}')
    return f'{f(s.median())} ({f(s.quantile(.25))}–{f(s.quantile(.75))})'


def main():
    d = fp_harms.load()
    soc = d[d.cell == 'SOC']
    poc = cell(d, 'baseline', 'baseline', 'none')
    mod = cell(d, 'moderate', 'moderate', 'moderate')
    high = cell(d, 'high', 'high', 'high')
    lines = ['# Headline numbers', '', 'Median (IQR) across parameter sets; 2027–2040; 98% specificity unless stated.', '']

    # The false-positive share, from SOC to POC to all high
    lines += ['## False-positive share of female index cases', '',
              f'- SOC: {fmt(soc.fp_share_f, True)}',
              f'- POC alone: {fmt(poc.fp_share_f, True)}',
              f'- All moderate: {fmt(mod.fp_share_f, True)}',
              f'- All high: {fmt(high.fp_share_f, True)}']
    back = (high.set_index('draw').fp_share_f - poc.set_index('draw').fp_share_f) / (soc.set_index('draw').fp_share_f - poc.set_index('draw').fp_share_f)
    lines += [f'- All high, share of the way back to SOC: {fmt(back, True)}',
              f'- Men, SOC / POC alone / all high: {fmt(soc.fp_share_m, True)} / {fmt(poc.fp_share_m, True)} / {fmt(high.fp_share_m, True)}', '']

    # Presenter prevalence
    lines += ['## NG/CT prevalence among women presenting with discharge', '',
              f'- SOC: {fmt(soc.pres_prev_ngct_f, True)}',
              f'- POC alone: {fmt(poc.pres_prev_ngct_f, True)}',
              f'- All high: {fmt(high.pres_prev_ngct_f, True)}', '']

    # Infections averted and unnecessary treatment
    ngct_unnec = lambda x: x.ng_new_treated_unnecessary + x.ct_new_treated_unnecessary
    red = 1 - ngct_unnec(poc).values / ngct_unnec(soc.set_index('draw').loc[poc.draw]).values
    lines += ['## Infections averted (NG + CT + TV) vs SOC', '',
              f'- POC alone: {fmt(poc.pct_inf_averted, True)}',
              f'- All moderate: {fmt(mod.pct_inf_averted, True)}',
              f'- All high: {fmt(high.pct_inf_averted, True)}',
              f'- Unnecessary NG/CT treatment, POC alone vs SOC: {fmt(red, True)} reduction', '']

    # Notifications
    lines += ['## False-positive partner notifications per year (scaled to Zimbabwe)', '',
              f'- SOC: {fmt(soc.unnec_notified / YEARS)}',
              f'- POC alone: {fmt(poc.unnec_notified / YEARS)}',
              f'- All high: {fmt(high.unnec_notified / YEARS)}', '']

    # Shapley
    shap = pd.read_csv(RES / 'shapley.csv')
    lines += ['## Shapley shares of infections averted beyond POC alone', '']
    for lvl in ('moderate', 'high'):
        s = shap[shap.level == lvl]
        parts = ', '.join(f'{name} {fmt(s[col] / s.total, True)}' for col, name in
                          (('phi_care', 'care-seeking'), ('phi_pn', 'PN'), ('phi_bp', 'condom counselling')))
        lines.append(f'- All {lvl}: {parts}')
    lines.append('')

    # Specificity sweep (Table 2) and the specificity needed
    lines += ['## Table 2: specificity sweep', '',
              '| Scenario | Specificity | Infections averted | FP share, female index | FP notifications / yr | Presenter NG/CT prevalence |',
              '|---|---|---|---|---|---|']
    target = poc.fp_share_f.median()
    needed = None
    for name, args in (('POC alone', ('baseline', 'baseline', 'none')), ('All moderate', ('moderate', 'moderate', 'moderate')), ('All high', ('high', 'high', 'high'))):
        meds = []
        for spec in sorted(SPEC_SWEEP):
            c = cell(d, *args, spec=spec)
            if not len(c):
                continue
            meds.append((spec, c.fp_share_f.median()))
            lines.append(f'| {name} | {100*spec:g}% | {fmt(c.pct_inf_averted, True)} | {fmt(c.fp_share_f, True)} | '
                         f'{fmt(c.unnec_notified / YEARS)} | {fmt(c.pres_prev_ngct_f, True)} |')
        if name == 'All high' and meds:
            specs, fps = zip(*meds)
            if min(fps) <= target <= max(fps):
                needed = float(np.interp(target, fps[::-1], specs[::-1]))  # fp falls as spec rises
    lines += ['', f'- Specificity at which the all-high FP share equals the POC-alone level at 98% ({100*target:.1f}%): '
              + (f'{100*needed:.1f}% (linear interpolation of medians across the sweep)' if needed else 'outside the swept range'), '']

    # Harm-benefit
    cells = fp_harms.summarise(d)
    pocc = cells[cells.cell != 'SOC'].copy()
    pocc = pocc[np.isclose(pocc.spec.astype(float), BASE_SPEC)]
    r = pocc.sort_values('unnec_notified_per_inf_averted_med')
    lines += ['## Unnecessary notifications per infection averted (98% specificity)', '',
              f'- Range of cell medians: {r.unnec_notified_per_inf_averted_med.min():.3g} to {r.unnec_notified_per_inf_averted_med.max():.3g}',
              f'- Lowest: {r.cell.iloc[0]}; highest: {r.cell.iloc[-1]}', '']

    out = RES / 'headlines.md'
    out.write_text('\n'.join(lines))
    print('\n'.join(lines))
    print(f'\nwrote {out}')


if __name__ == '__main__':
    main()
