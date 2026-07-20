"""Data prep for the Quarto dashboard.

Reads the committed results tables directly (no JSON export step, no JS
transforms) and exposes tidy long frames + median/IQR aggregation helpers.
Replaces dashboard/scripts/export_data.py + dashboard/src/utils/dataTransforms.js.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[0]
RESULTS = REPO_ROOT / 'results'

DISEASES = [
    ('ng', 'Gonorrhoea'),
    ('ct', 'Chlamydia'),
    ('tv', 'Trichomoniasis'),
    ('syph', 'Syphilis'),
]
DISEASE_LABEL = dict(DISEASES)

PREV_COL = {d: f'{d}_prev_end' for d, _ in DISEASES}
PREV_COL['syph'] = 'syph_sti_prev_end'


# ---------------------------------------------------------------------------
# Load + reshape
# ---------------------------------------------------------------------------

def load_scenarios_long():
    """One row per (draw, arm, disease, metric); plus pn notification rows."""
    df = pd.read_csv(RESULTS / 'scenarios.kavg.csv')
    recs = []
    for _, row in df.iterrows():
        arm = dict(care=row['care'], pn=row['pn'], bp=row['bp'], poc=bool(row['poc']),
                   draw=int(row['draw']))
        for d, _ in DISEASES:
            treated = row[f'{d}_new_treated']
            unnec = row[f'{d}_new_treated_unnecessary']
            over = (unnec / treated) if treated else np.nan
            recs += [
                {**arm, 'disease': d, 'metric': 'prevalence', 'value': row[PREV_COL[d]]},
                {**arm, 'disease': d, 'metric': 'new_inf', 'value': row[f'{d}_new_inf']},
                {**arm, 'disease': d, 'metric': 'overtreatment', 'value': over},
            ]
        notified = row['pn_new_notified']
        notified_no_sti = row['pn_new_notified_no_sti']
        idx_tot = row['pn_new_index_total']
        idx_no_sti = row['pn_new_index_no_sti']
        over_n = (notified_no_sti / notified) if notified else np.nan
        denom = idx_tot - idx_no_sti
        under_n = (1 - (notified - notified_no_sti) / denom) if denom else np.nan
        recs += [
            {**arm, 'disease': 'pn', 'metric': 'over_notification', 'value': over_n},
            {**arm, 'disease': 'pn', 'metric': 'under_notification', 'value': under_n},
        ]
    return pd.DataFrame(recs)


def load_timeseries():
    """Prevalence + new-infection trajectories per (arm, disease, year).

    Sourced from ``data/timeseries.json`` — the median trajectories whose
    end-of-horizon values match the scalar table ``scenarios.kavg.csv``
    (e.g. ng 2040 prevalence 0.0176 == ng_prev_end). NOTE: the committed
    ``results/scenarios_timeseries.parquet`` is from a *different* run (draws
    14/16/47, 126 cells) than the scalar table (draws 75/78/236/263/343, 65
    cells), so it does not match the bars and is deliberately not used here.
    Regenerate that parquet from the current run to switch back to it.
    """
    recs = json.loads((HERE / 'data' / 'timeseries.json').read_text())
    df = pd.DataFrame(recs).rename(
        columns={'care_level': 'care', 'pn_level': 'pn', 'bp_level': 'bp'})
    return df[['care', 'pn', 'bp', 'poc', 'disease', 'metric', 'year', 'value']]


def load_diagnostic_performance():
    return pd.read_csv(RESULTS / 'slide4_diagnostic_performance.csv')


# ---------------------------------------------------------------------------
# Aggregation (median + IQR across draws) — mirrors dataTransforms.js
# ---------------------------------------------------------------------------

def _med_iqr(values):
    v = pd.Series(values).dropna().to_numpy()
    if len(v) == 0:
        return dict(median=np.nan, p25=np.nan, p75=np.nan)
    return dict(median=float(np.quantile(v, 0.5)),
                p25=float(np.quantile(v, 0.25)),
                p75=float(np.quantile(v, 0.75)))


def _arm_mask(df, poc, care='baseline', pn='baseline', bp='none'):
    """SOC = every poc-False row; POC = the one matching arm."""
    if not poc:
        return df['poc'].eq(False)
    return (df['poc'].eq(True) & df['care'].eq(care)
            & df['pn'].eq(pn) & df['bp'].eq(bp))


def preset_bar(long, presets, disease, metric):
    """DataFrame [label, is_soc, median, p25, p75] over a list of preset dicts."""
    rows = []
    for p in presets:
        poc = p['key'] != 'soc'
        sub = long[(long['disease'] == disease) & (long['metric'] == metric)
                   & _arm_mask(long, poc, p.get('care', 'baseline'),
                               p.get('pn', 'baseline'), p.get('bp', 'none'))]
        rows.append({'label': p['label'], 'is_soc': not poc, **_med_iqr(sub['value'])})
    return pd.DataFrame(rows)


def preset_notification(long, presets):
    """DataFrame [label, is_soc, over_*, under_*] for the PN over/under chart."""
    rows = []
    for p in presets:
        poc = p['key'] != 'soc'
        m = _arm_mask(long, poc, p.get('care', 'baseline'),
                      p.get('pn', 'baseline'), p.get('bp', 'none'))
        over = long[(long['disease'] == 'pn') & (long['metric'] == 'over_notification') & m]
        under = long[(long['disease'] == 'pn') & (long['metric'] == 'under_notification') & m]
        o, u = _med_iqr(over['value']), _med_iqr(under['value'])
        rows.append({'label': p['label'], 'is_soc': not poc,
                     **{f'over_{k}': v for k, v in o.items()},
                     **{f'under_{k}': v for k, v in u.items()}})
    return pd.DataFrame(rows)


def preset_ts(ts, presets, disease, metric):
    """Long frame [label, is_soc, year, value] for line charts."""
    out = []
    for p in presets:
        poc = p['key'] != 'soc'
        m = ((ts['disease'] == disease) & (ts['metric'] == metric)
             & _arm_mask(ts, poc, p.get('care', 'baseline'),
                         p.get('pn', 'baseline'), p.get('bp', 'none')))
        sub = ts[m].sort_values('year')
        for _, r in sub.iterrows():
            out.append({'label': p['label'], 'is_soc': not poc,
                        'year': int(r['year']), 'value': r['value']})
    return pd.DataFrame(out)
