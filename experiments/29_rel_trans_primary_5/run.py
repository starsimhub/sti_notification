"""
Exp 29 — rel_trans_primary=5, extended early latent (22-24mo), SyphTx fix.

Hand-pick at exp 28's config + one parameter override: rel_trans_primary=5.
Structural changes baked into stisim:
  - SyphTx clears non-trep within 6-12 mo of early-stage treatment
  - dur_early default 12-14mo -> 22-24mo (WHO Europe early-latent boundary)
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json, pickle, time
from pathlib import Path

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP24))

import numpy as np
import pandas as pd
import sciris as sc

# Reuse exp 24's run_one (handles instrumentation + FSW/risk-group storage)
from run import run_one as run_one_exp24, CONFIG as CONFIG24, SEEDS  # noqa: E402

# Override exp 24's CONFIG with rel_trans_primary=5 — patch the imported dict
CONFIG = dict(CONFIG24)
CONFIG['syph.rel_trans_primary'] = 5.0


# Inject into exp 24's namespace so its run_one uses the modified config
import run as exp24_module  # noqa: E402
exp24_module.CONFIG = CONFIG

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
SERIES_PKL = OUTPUTS / 'series.pkl'
STAGE_CSV  = OUTPUTS / 'stage_shares.csv'
RESULTS    = OUTPUTS / 'results.json'


def main():
    sc.heading('Exp 29 — rel_trans_primary=5 + dur_early 22-24mo + SyphTx fix')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    print('Config (exp 28 hand-pick + rel_trans_primary=5):')
    for k, v in CONFIG.items():
        flag = '  *' if k == 'syph.rel_trans_primary' else ''
        print(f'  {k:42s} = {v}{flag}')

    summaries, all_series, all_stage_rows = [], {}, []
    t0 = time.time()
    for seed in SEEDS:
        print(f'  -> seed {seed} ...', flush=True)
        summary, series, stage_rows = run_one_exp24(seed)
        summaries.append(summary)
        all_series[seed] = series
        all_stage_rows.extend(stage_rows)
        print(f"     FSW={summary['fsw_prev_2019']:.3f}  "
              f"nontrep_f={summary['nontrep_f_2016']:.4f}  "
              f"trep_f={summary['trep_f_2016']:.4f}  "
              f"primary={summary['stage_share_primary_plateau']:.2f} "
              f"sec={summary['stage_share_secondary_plateau']:.2f} "
              f"early_lat={summary['stage_share_early_latent_plateau']:.2f}")
    print(f'  total {time.time()-t0:.1f}s')

    pd.DataFrame(all_stage_rows).to_csv(STAGE_CSV, index=False)
    with SERIES_PKL.open('wb') as f:
        pickle.dump(all_series, f)

    df = pd.DataFrame(summaries)
    aggregates = {col: float(df[col].mean()) for col in df.columns if col != 'seed'}
    out = {'config': CONFIG, 'seeds': SEEDS,
           'per_seed': summaries, 'mean': aggregates}
    RESULTS.write_text(json.dumps(out, indent=2))

    exp28_mean = json.load(open(PROJECT_ROOT / 'experiments' /
                                '28_syphtx_clears_nontrep' / 'outputs' /
                                'results.json'))['mean']

    print('\n=== EXP 29 vs EXP 28 (3-seed mean) ===')
    print(f"{'metric':36s}  {'exp 28':>10s}  {'exp 29':>10s}  {'delta':>10s}")
    for metric in ['fsw_prev_2019', 'nontrep_f_2016', 'trep_f_2016',
                   'stage_share_primary_plateau', 'stage_share_secondary_plateau',
                   'stage_share_early_latent_plateau',
                   'stage_share_late_latent_plateau',
                   'new_inf_2030_2040_mean',
                   'overall_prev_f_2035_2040_mean']:
        v28 = exp28_mean.get(metric, np.nan)
        v29 = aggregates.get(metric, np.nan)
        delta = v29 - v28
        print(f'  {metric:36s}  {v28:>10.4f}  {v29:>10.4f}  {delta:>+10.4f}')

    print('\n=== LOOSE TARGETS (relaxed stage bands) ===')
    checks = [
        ('FSW prev 2019',         aggregates['fsw_prev_2019'],            (0.20, 0.40)),
        ('nontrep_f 2016',        aggregates['nontrep_f_2016'],           (0.01, 0.03)),
        ('trep_f 2016',           aggregates['trep_f_2016'],              (0.05, 0.10)),
        ('primary share',         aggregates['stage_share_primary_plateau'], (0.45, 0.65)),
        ('secondary share',       aggregates['stage_share_secondary_plateau'], (0.25, 0.45)),
    ]
    all_pass = True
    for label, val, (lo, hi) in checks:
        ok = lo <= val <= hi
        all_pass = all_pass and ok
        print(f'  {label:24s}: {val:.4f}  [{lo}, {hi}]  {"PASS" if ok else "MISS"}')
    el_share = aggregates['stage_share_early_latent_plateau']
    el_ok = el_share <= 0.15
    all_pass = all_pass and el_ok
    print(f'  early latent share      : {el_share:.4f}  [<=0.15]  {"PASS" if el_ok else "MISS"}')
    sustain_ok = (aggregates['new_inf_2030_2040_mean'] > 0 and
                  aggregates['overall_prev_f_2035_2040_mean'] >= 0.001)
    all_pass = all_pass and sustain_ok
    print(f'  sustained to 2040       : {aggregates["new_inf_2030_2040_mean"]:.2f}  {"PASS" if sustain_ok else "MISS"}')
    print(f'\nOVERALL: {"PASS" if all_pass else "DIAGNOSTIC MISS"}')


if __name__ == '__main__':
    main()
