"""
Exp 35 — Build the decision-analysis ensemble.

Two-phase:
  Phase 1: 1500 LHS draws (seed=43), single seed each. Identifies
           candidates: sustained AND n_pass >= 5 (backfill from
           4+/9 sustained if <100).
  Phase 2: re-run each selected candidate with 3 seeds. Output
           per-(draw, seed) results + per-draw means.

Outputs the working ensemble for PN decision analysis.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json, time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
from scipy.stats import qmc

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
sys.path.insert(0, str(EXP24))

from model import make_sim
from priors import calib_pars
from interventions import ANC_PROBS_REALISTIC
from run import set_pars_local, grab  # noqa: E402

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
EVENTS_DIR = OUTPUTS / 'events'

PHASE1_JSONL  = OUTPUTS / 'phase1_results.jsonl'
PHASE1_CSV    = OUTPUTS / 'phase1_priors.csv'
ENS_DRAWS_CSV = OUTPUTS / 'ensemble_draws.csv'
ENS_JSONL     = OUTPUTS / 'ensemble_results.jsonl'
ENS_SUMMARY   = OUTPUTS / 'ensemble_summary.csv'
ENS_META      = OUTPUTS / 'ensemble_selection.json'

# Phase 1
P1_N_DRAWS = int(os.environ.get('P1_N_DRAWS', 1500))
P1_SEED    = int(os.environ.get('P1_SEED', 43))

# Phase 2
P2_SEEDS_PER_DRAW = int(os.environ.get('P2_SEEDS', 3))
P2_SEED_BASE      = int(os.environ.get('P2_SEED_BASE', 100_000))
ENSEMBLE_TARGET   = int(os.environ.get('ENS_TARGET', 100))

# Common
N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))

SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'

TARGET_BANDS = {
    'fsw_band':           (0.20, 0.40),
    'nontrep_band':       (0.01, 0.05),
    'trep_band':          (0.05, 0.10),
    'primary_band':       (0.45, 0.65),
    'secondary_band':     (0.25, 0.45),
    'hiv_pos_trep_band':  (0.05, 0.09),
    'hiv_trep_ratio_band': (3.0, 6.0),
}
EARLY_LAT_MAX = 0.15


# ----------------------------------------------------------------------------
# Prior sampling
# ----------------------------------------------------------------------------
def generate_prior_draws(n_draws, seed):
    names = list(calib_pars.keys())
    bounds = []
    for name, (_, lo, hi, log_scale) in calib_pars.items():
        if log_scale:
            bounds.append((np.log(lo), np.log(hi)))
        else:
            bounds.append((lo, hi))
    sampler = qmc.LatinHypercube(d=len(names), seed=seed)
    pts = sampler.random(n_draws)
    rows = []
    for i in range(n_draws):
        row = {'draw_idx': i}
        for j, name in enumerate(names):
            lo, hi = bounds[j]
            val = lo + pts[i, j] * (hi - lo)
            if calib_pars[name][3]:
                row[f'log_{name}'] = val
            else:
                row[name] = val
        rows.append(row)
    return pd.DataFrame(rows)


def row_to_sim_pars(row):
    sim_pars = {}
    for col, val in row.items():
        if col in ('draw_idx', 'seed'):
            continue
        if col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        elif '.' in col:
            sim_pars[col] = float(val)
    return sim_pars


# ----------------------------------------------------------------------------
# Single-sim runner — works for both phases
# ----------------------------------------------------------------------------
def find_analyzer(sim, name):
    return getattr(sim.analyzers, name, None)


def stage_shares_from_matrix(matrix):
    by_stage = {'primary': 0, 'secondary': 0, 'early_latent': 0,
                'late_latent': 0, 'unknown': 0}
    for (_src, _dst, stage), n in matrix.items():
        by_stage[stage] = by_stage.get(stage, 0) + n
    total = sum(v for k, v in by_stage.items() if k != 'unknown') or 1
    return {k: v / total for k, v in by_stage.items() if k != 'unknown'}


def top_spreader_count(src_count):
    if not src_count:
        return None
    counts = sorted(src_count.values(), reverse=True)
    total = sum(counts)
    if total == 0:
        return None
    cum = 0
    for i, c in enumerate(counts):
        cum += c
        if cum >= 0.5 * total:
            return i + 1
    return len(counts)


def run_one(task):
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    seed = task['seed']
    save_events_as = task.get('save_events_as')  # filename suffix
    try:
        symp_test = pd.read_csv(SYMP_TEST_CSV)
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1,
                       syph_symp_test_prob=symp_test,
                       syph_anc_probs=ANC_PROBS_REALISTIC)
        set_pars_local(sim, sim_pars)

        for mod in sim.pars['diseases']:
            if getattr(mod, 'name', None) == 'syph':
                mod.store_sw = True
                break

        sim.run()

        r = sim.results['syph']
        yrs, prev_f      = grab(r, 'prevalence_f')
        yrs_inf, new_inf = grab(r, 'new_infections')
        _, fsw_prev      = grab(r, 'prevalence_sw')
        _, client_prev   = grab(r, 'prevalence_client')
        _, nontrep_f     = grab(r, 'nontrep_prevalence_15_64_f')
        _, trep_f        = grab(r, 'trep_prevalence_15_64_f')

        r_trep    = sim.results['syph_hiv_trep']
        r_nontrep = sim.results['syph_hiv_nontrep']
        yrs_ana, trep_has_hiv = grab(r_trep, 'syph_prev_has_hiv')
        _, trep_no_hiv        = grab(r_trep, 'syph_prev_no_hiv')
        _, nontrep_has_hiv    = grab(r_nontrep, 'syph_prev_has_hiv')
        _, nontrep_no_hiv     = grab(r_nontrep, 'syph_prev_no_hiv')

        _, hiv_prev = grab(sim.results['hiv'], 'prevalence')

        def at(arr, ys, year):
            i = np.argmin(np.abs(ys - year))
            return float(arr[i])

        def avg(arr, ys, y1, y2):
            m = (ys >= y1) & (ys < y2)
            return float(np.nanmean(arr[m])) if m.any() else np.nan

        ana = find_analyzer(sim, 'syph_transmission_events')
        matrix = dict(ana.matrix) if ana is not None else {}
        src_count = dict(ana.src_count) if ana is not None else {}
        plateau_shares = stage_shares_from_matrix(matrix)

        if ana is not None and save_events_as:
            EVENTS_DIR.mkdir(parents=True, exist_ok=True)
            (EVENTS_DIR / save_events_as).write_text(json.dumps(ana.as_dict()))

        fsw_v    = at(fsw_prev, yrs, 2019)
        ntr_v    = at(nontrep_f, yrs, 2016)
        tr_v     = at(trep_f, yrs, 2016)
        prim_v   = plateau_shares.get('primary', 0.0)
        sec_v    = plateau_shares.get('secondary', 0.0)
        el_v     = plateau_shares.get('early_latent', 0.0)
        ll_v     = plateau_shares.get('late_latent', 0.0)
        ni_late  = avg(new_inf, yrs_inf, 2030, 2040)
        pf_late  = avg(prev_f, yrs, 2035, 2040)
        sust     = bool(ni_late > 0 and pf_late >= 0.001)

        hiv_pos_trep = at(trep_has_hiv, yrs_ana, 2016)
        hiv_neg_trep = at(trep_no_hiv, yrs_ana, 2016)
        hiv_pos_nontrep = at(nontrep_has_hiv, yrs_ana, 2016)
        hiv_neg_nontrep = at(nontrep_no_hiv, yrs_ana, 2016)
        hiv_trep_ratio = (hiv_pos_trep / hiv_neg_trep) if hiv_neg_trep > 0 else np.nan

        passes = {
            'fsw_band':       TARGET_BANDS['fsw_band'][0]      <= fsw_v <= TARGET_BANDS['fsw_band'][1],
            'nontrep_band':   TARGET_BANDS['nontrep_band'][0]  <= ntr_v <= TARGET_BANDS['nontrep_band'][1],
            'trep_band':      TARGET_BANDS['trep_band'][0]     <= tr_v  <= TARGET_BANDS['trep_band'][1],
            'primary_band':   TARGET_BANDS['primary_band'][0]  <= prim_v <= TARGET_BANDS['primary_band'][1],
            'secondary_band': TARGET_BANDS['secondary_band'][0] <= sec_v <= TARGET_BANDS['secondary_band'][1],
            'early_lat_band': el_v <= EARLY_LAT_MAX,
            'sustained':      sust,
            'hiv_pos_trep_band':  TARGET_BANDS['hiv_pos_trep_band'][0]  <= hiv_pos_trep <= TARGET_BANDS['hiv_pos_trep_band'][1],
            'hiv_trep_ratio_band': (not np.isnan(hiv_trep_ratio)) and TARGET_BANDS['hiv_trep_ratio_band'][0] <= hiv_trep_ratio <= TARGET_BANDS['hiv_trep_ratio_band'][1],
        }
        n_pass = sum(passes.values())

        return {
            'draw_idx': draw_idx, 'seed': seed,
            'fsw_prev_2019':   fsw_v,
            'nontrep_f_2016':  ntr_v,
            'trep_f_2016':     tr_v,
            'primary_share':   prim_v,
            'secondary_share': sec_v,
            'early_lat_share': el_v,
            'late_lat_share':  ll_v,
            'client_prev_2016': at(client_prev, yrs, 2016),
            'overall_prev_f_2035_2040_mean': pf_late,
            'new_inf_2030_2040_mean': ni_late,
            'hiv_pos_trep_2016':    hiv_pos_trep,
            'hiv_neg_trep_2016':    hiv_neg_trep,
            'hiv_pos_nontrep_2016': hiv_pos_nontrep,
            'hiv_neg_nontrep_2016': hiv_neg_nontrep,
            'hiv_trep_ratio_2016':  float(hiv_trep_ratio) if not np.isnan(hiv_trep_ratio) else None,
            'hiv_prev_2010_2020':   avg(hiv_prev, yrs, 2010, 2020),
            'n_top_spreaders_50pct': top_spreader_count(src_count),
            'passes': passes,
            'n_pass': n_pass,
            'status': 'ok',
        }
    except Exception as e:
        return {'draw_idx': draw_idx, 'seed': seed,
                'status': f'error: {type(e).__name__}: {e}'}


def run_pool(tasks, out_jsonl, label):
    print(f'\n{label}: running {len(tasks)} sims on {N_WORKERS} workers...')
    t0 = time.time()
    summaries = []
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with out_jsonl.open('w') as fout:
            for i, summary in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(summary) + '\n')
                fout.flush()
                summaries.append(summary)
                if i % 50 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i:4d}/{len(tasks)}] {elapsed:.0f}s  eta={eta:.0f}s',
                          flush=True)
    print(f'  done in {time.time()-t0:.1f}s')
    return summaries


# ----------------------------------------------------------------------------
# Phase 1: candidate discovery
# ----------------------------------------------------------------------------
def phase1():
    sc.heading(f'PHASE 1: {P1_N_DRAWS}-draw LHS, seed={P1_SEED}, '
               f'{len(calib_pars)} priors')
    prior_df = generate_prior_draws(P1_N_DRAWS, P1_SEED)
    prior_df.to_csv(PHASE1_CSV, index=False)

    tasks = []
    for _, row in prior_df.iterrows():
        di = int(row['draw_idx'])
        tasks.append({'draw_idx': di,
                      'sim_pars': row_to_sim_pars(row),
                      'seed': di * 1000,
                      'save_events_as': None})  # skip events for phase 1 (size)

    run_pool(tasks, PHASE1_JSONL, 'Phase 1')


# ----------------------------------------------------------------------------
# Ensemble selection
# ----------------------------------------------------------------------------
def select_ensemble():
    sc.heading('ENSEMBLE SELECTION')
    rows = [json.loads(l) for l in PHASE1_JSONL.open()]
    df = pd.DataFrame(rows)
    df = df[df['status'] == 'ok'].copy()
    df['sustained'] = df['passes'].apply(lambda p: p.get('sustained', False))
    sustained = df[df['sustained']]
    primary = sustained[sustained['n_pass'] >= 5]
    backfill = sustained[(sustained['n_pass'] == 4)]

    print(f'  Phase 1 ok:              {len(df)}/{P1_N_DRAWS}')
    print(f'  sustained:               {len(sustained)}')
    print(f'  sustained AND 5+/9:      {len(primary)}')
    print(f'  sustained AND ==4/9:     {len(backfill)}')

    selected = primary.copy()
    used_backfill = 0
    if len(selected) < ENSEMBLE_TARGET:
        need = ENSEMBLE_TARGET - len(selected)
        take = backfill.head(need)
        selected = pd.concat([selected, take], ignore_index=True)
        used_backfill = len(take)
        print(f'  backfilled with 4/9:     {used_backfill}')

    print(f'  ENSEMBLE size:           {len(selected)}')

    # Save selection
    priors = pd.read_csv(PHASE1_CSV)
    sel_with_priors = priors[priors['draw_idx'].isin(selected['draw_idx'])]
    sel_with_priors.to_csv(ENS_DRAWS_CSV, index=False)

    meta = {
        'p1_n_draws': P1_N_DRAWS,
        'p1_seed': P1_SEED,
        'p1_n_ok': int(len(df)),
        'n_sustained': int(len(sustained)),
        'n_sustained_5plus': int(len(primary)),
        'n_backfill_used': int(used_backfill),
        'ensemble_size': int(len(selected)),
        'ensemble_target': ENSEMBLE_TARGET,
    }
    ENS_META.write_text(json.dumps(meta, indent=2))
    return sel_with_priors


# ----------------------------------------------------------------------------
# Phase 2: ensemble re-run with 3 seeds
# ----------------------------------------------------------------------------
def phase2(ensemble_priors):
    sc.heading(f'PHASE 2: {len(ensemble_priors)} candidates × {P2_SEEDS_PER_DRAW} seeds')
    tasks = []
    for _, row in ensemble_priors.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row)
        for s_idx in range(P2_SEEDS_PER_DRAW):
            seed = P2_SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di,
                          'sim_pars': sim_pars,
                          'seed': seed,
                          'save_events_as': f'events_{di:04d}_seed{s_idx}.json'})

    run_pool(tasks, ENS_JSONL, 'Phase 2')

    # Aggregate per-draw mean across seeds
    rows = [json.loads(l) for l in ENS_JSONL.open()]
    df = pd.DataFrame(rows)
    df_ok = df[df['status'] == 'ok'].copy()
    numeric = [c for c in df_ok.columns
               if c not in ('draw_idx','seed','passes','status') and
               pd.api.types.is_numeric_dtype(df_ok[c])]
    grouped = df_ok.groupby('draw_idx')[numeric].mean().reset_index()
    # Also count seeds and any-seed pass-rate per draw
    grouped['n_seeds_ok'] = df_ok.groupby('draw_idx').size().reset_index(drop=True)
    # Per-target seed-mean pass rates
    targets = list(TARGET_BANDS.keys()) + ['early_lat_band','sustained']
    for t in targets:
        if t == 'early_lat_band' or t == 'sustained':
            continue
    for t in ['fsw_band','nontrep_band','trep_band','primary_band','secondary_band',
              'early_lat_band','sustained','hiv_pos_trep_band','hiv_trep_ratio_band']:
        grouped[f'pass_{t}'] = df_ok.groupby('draw_idx')['passes'].apply(
            lambda s: sum(p.get(t, False) for p in s) / len(s)).reset_index(drop=True)
    grouped['n_pass_mean'] = df_ok.groupby('draw_idx')['n_pass'].mean().reset_index(drop=True)
    grouped.to_csv(ENS_SUMMARY, index=False)
    print(f'\nWrote per-draw summary to {ENS_SUMMARY}')

    # Report
    print(f'\n=== ENSEMBLE STATS (per-draw means across {P2_SEEDS_PER_DRAW} seeds) ===')
    print(f'  draws:                  {len(grouped)}')
    print(f'  median nontrep_f:       {grouped["nontrep_f_2016"].median():.3f}')
    print(f'  median trep_f:          {grouped["trep_f_2016"].median():.3f}')
    print(f'  median fsw_prev_2019:   {grouped["fsw_prev_2019"].median():.3f}')
    print(f'  median HIV ratio:       {grouped["hiv_trep_ratio_2016"].median():.3f}')
    print(f'  median n_pass:          {grouped["n_pass_mean"].median():.2f}')
    print(f'  draws sustained 3/3:    {(grouped["pass_sustained"] == 1.0).sum()}')


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    phase1()
    ensemble = select_ensemble()
    phase2(ensemble)


if __name__ == '__main__':
    main()
