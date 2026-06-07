"""
Exp 28 — re-run exp 24's hand-pick with SyphTx-clears-nontrep patch.

The stisim patch adds a Dist nontrep_revert_months=ss.uniform(6,12) on
SyphTx; in change_states, early-stage (primary/secondary/early-latent)
treated agents get ti_nontrep_end = ti + steps_to_revert. This fixes
the bug where treated agents stayed nontrep=True for life.

Compares directly to exp 24 (same config, same seeds) to isolate the
effect of the patch.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
from pathlib import Path

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'

# Reuse exp 24's run_one verbatim — same config, same instrumentation
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP24))

import json, pickle, time
import numpy as np
import pandas as pd
import sciris as sc

from run import run_one, CONFIG, SEEDS  # noqa: E402

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
SERIES_PKL = OUTPUTS / 'series.pkl'
STAGE_CSV  = OUTPUTS / 'stage_shares.csv'
RESULTS    = OUTPUTS / 'results.json'


def main():
    sc.heading('Exp 28 — exp 24 hand-pick + SyphTx-clears-nontrep patch')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    print('Same hand-picked config as exp 24:')
    for k, v in CONFIG.items():
        print(f'  {k:42s} = {v}')
    print('Only diff vs exp 24: stisim SyphTx now clears non-trep within 6-12 mo of early-stage treatment.')

    summaries, all_series, all_stage_rows = [], {}, []
    t0 = time.time()
    for seed in SEEDS:
        print(f'  -> seed {seed} ...', flush=True)
        summary, series, stage_rows = run_one(seed)
        summaries.append(summary)
        all_series[seed] = series
        all_stage_rows.extend(stage_rows)
        print(f"     FSW={summary['fsw_prev_2019']:.3f}  "
              f"nontrep_f={summary['nontrep_f_2016']:.4f}  "
              f"trep_f={summary['trep_f_2016']:.4f}  "
              f"primary={summary['stage_share_primary_plateau']:.2f} "
              f"sec={summary['stage_share_secondary_plateau']:.2f}")
    print(f'  total {time.time()-t0:.1f}s')

    pd.DataFrame(all_stage_rows).to_csv(STAGE_CSV, index=False)
    with SERIES_PKL.open('wb') as f:
        pickle.dump(all_series, f)

    df = pd.DataFrame(summaries)
    aggregates = {col: float(df[col].mean()) for col in df.columns if col != 'seed'}
    out = {'config': CONFIG, 'seeds': SEEDS,
           'per_seed': summaries, 'mean': aggregates}
    RESULTS.write_text(json.dumps(out, indent=2))

    # Loose target checks + comparison with exp 24
    exp24_mean = json.load(open(EXP24 / 'outputs' / 'results.json'))['mean']

    print('\n=== EXP 28 vs EXP 24 (3-seed mean) ===')
    print(f"{'metric':30s}  {'exp 24':>10s}  {'exp 28':>10s}  {'delta':>10s}")
    for metric in ['fsw_prev_2019', 'nontrep_f_2016', 'trep_f_2016',
                   'stage_share_primary_plateau', 'stage_share_secondary_plateau',
                   'new_inf_2030_2040_mean', 'overall_prev_f_2035_2040_mean']:
        v24 = exp24_mean.get(metric, np.nan)
        v28 = aggregates.get(metric, np.nan)
        delta = v28 - v24
        print(f'  {metric:30s}  {v24:>10.4f}  {v28:>10.4f}  {delta:>+10.4f}')

    print('\n=== LOOSE TARGET BANDS ===')
    checks = [
        ('FSW prev 2019',            aggregates['fsw_prev_2019'],            (0.20, 0.40)),
        ('nontrep_f 2016',           aggregates['nontrep_f_2016'],           (0.01, 0.03)),
        ('trep_f 2016',              aggregates['trep_f_2016'],              (0.05, 0.10)),
        ('primary share plateau',    aggregates['stage_share_primary_plateau'], (0.50, 0.65)),
        ('secondary share plateau',  aggregates['stage_share_secondary_plateau'], (0.25, 0.40)),
    ]
    all_pass = True
    for label, val, (lo, hi) in checks:
        ok = lo <= val <= hi
        all_pass = all_pass and ok
        print(f'  {label:28s}: {val:.4f}  [{lo}, {hi}]  {"PASS" if ok else "MISS"}')
    sustain_pass = (aggregates['new_inf_2030_2040_mean'] > 0 and
                    aggregates['overall_prev_f_2035_2040_mean'] >= 0.001)
    all_pass = all_pass and sustain_pass
    print(f'  sustained to 2040           : {aggregates["new_inf_2030_2040_mean"]:.2f}  {"PASS" if sustain_pass else "MISS"}')
    print(f'\nOVERALL: {"PASS" if all_pass else "DIAGNOSTIC MISS"}')


if __name__ == '__main__':
    main()
