"""Export scenarios.kavg.csv + scenario ladder definitions to dashboard/src/data/."""

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]   # sti_notification/
DATA_DIR = Path(__file__).resolve().parents[1] / 'src' / 'data'

sys.path.insert(0, str(REPO_ROOT))
from scenarios import (          # noqa: E402
    CARE_SEEKING, PN_INTENSITY, BUNDLED_PREVENTION,
    CARE_LEVELS, PN_LEVELS, BP_LEVELS,
)

DISEASES = ['hiv', 'ng', 'ct', 'tv', 'syph']
PREV_COL = {d: f'{d}_prev_end' for d in DISEASES}
PREV_COL['syph'] = 'syph_sti_prev_end'


def safe_div(numer, denom):
    if denom == 0 or pd.isna(denom):
        return None
    return numer / denom


def export_scenarios():
    df = pd.read_csv(REPO_ROOT / 'results' / 'scenarios.kavg.csv')
    records = []
    for _, row in df.iterrows():
        diseases = {}
        for d in DISEASES:
            new_inf = row[f'{d}_new_inf']
            new_treated = row[f'{d}_new_treated']
            new_treated_success = row[f'{d}_new_treated_success']
            new_treated_unnecessary = row[f'{d}_new_treated_unnecessary']
            diseases[d] = {
                'prev_end': row[PREV_COL[d]],
                'new_inf': new_inf,
                'new_treated': new_treated,
                'new_treated_success': new_treated_success,
                'new_treated_unnecessary': new_treated_unnecessary,
                'overtreatment_rate': safe_div(new_treated_unnecessary, new_treated),
                'undertreatment_rate': (
                    None if pd.isna(safe_div(new_treated_success, new_inf))
                    or safe_div(new_treated_success, new_inf) is None
                    else 1 - safe_div(new_treated_success, new_inf)
                ),
            }
        new_notified = row['pn_new_notified']
        notified_no_sti = row['pn_new_notified_no_sti']
        index_total = row['pn_new_index_total']
        index_no_sti = row['pn_new_index_no_sti']
        notification = {
            'new_notified': new_notified,
            'new_index_total': index_total,
            'over_notification_rate': safe_div(notified_no_sti, new_notified),
            'under_notification_rate': (
                None if safe_div(new_notified - notified_no_sti, index_total - index_no_sti) is None
                else 1 - safe_div(new_notified - notified_no_sti, index_total - index_no_sti)
            ),
        }
        records.append({
            'care_level': row['care'],
            'pn_level': row['pn'],
            'bp_level': row['bp'],
            'poc': bool(row['poc']),
            'draw': int(row['draw']),
            'diseases': diseases,
            'notification': notification,
        })
    dest = DATA_DIR / 'scenarios.json'
    dest.write_text(json.dumps(records, indent=2, allow_nan=False))
    print(f'Wrote {len(records)} records to {dest}')


def export_ladders():
    ladders = {
        'care': {'levels': CARE_LEVELS, 'values': CARE_SEEKING},
        'pn': {'levels': PN_LEVELS},
        'bp': {'levels': BP_LEVELS, 'values': {k: v['coverage'] for k, v in BUNDLED_PREVENTION.items()}},
    }
    dest = DATA_DIR / 'ladders.json'
    dest.write_text(json.dumps(ladders, indent=2))
    print(f'Wrote ladders.json to {dest}')


def export_diagnostic_performance():
    df = pd.read_csv(REPO_ROOT / 'results' / 'slide4_diagnostic_performance.csv')
    dest = DATA_DIR / 'diagnostic_performance.json'
    dest.write_text(json.dumps(df.to_dict(orient='records'), indent=2))
    print(f'Wrote {len(df)} records to {dest}')


if __name__ == '__main__':
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_scenarios()
    export_ladders()
    export_diagnostic_performance()
