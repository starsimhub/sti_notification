"""
Exp 36 — Robust ensemble extension.

Extends exp 35's 3-seed evaluation to the 370 sustained-in-Phase-1 draws
that weren't selected for Phase 2 (because their single-seed n_pass
was 1-4). Combined with exp 35's existing Phase 2 data, this gives
3-seed coverage for all 545 sustained-in-Phase-1 candidates.

Output: combined 3-seed table + the robust ensemble (sustained 3/3
AND mean n_pass >= 5).

Sim-runner helpers are duplicated from exp 35 rather than imported,
because multiprocessing workers can't import modules loaded via importlib.
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

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
EXP35 = PROJECT_ROOT / 'experiments' / '35_ensemble_build'
sys.path.insert(0, str(EXP24))

from model import make_sim
from interventions import ANC_PROBS_REALISTIC
from run import set_pars_local, grab  # noqa: E402  (from exp 24)

HERE          = THIS.parent
OUTPUTS       = HERE / 'outputs'
EVENTS_DIR    = OUTPUTS / 'events'
EXT_JSONL     = OUTPUTS / 'extension_results.jsonl'
COMBINED_CSV  = OUTPUTS / 'combined_3seed.csv'
ROBUST_CSV    = OUTPUTS / 'robust_ensemble.csv'
ROBUST_SUM    = OUTPUTS / 'robust_summary.csv'

EXP35_PHASE1  = EXP35 / 'outputs' / 'phase1_results.jsonl'
EXP35_PRIORS  = EXP35 / 'outputs' / 'phase1_priors.csv'
EXP35_PHASE2  = EXP35 / 'outputs' / 'ensemble_results.jsonl'

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))
P2_SEEDS_PER_DRAW = 3
P2_SEED_BASE      = 100_000

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
    save_events_as = task.get('save_events_as')
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


def identify_extension_draws():
    p1 = pd.DataFrame([json.loads(l) for l in EXP35_PHASE1.open()])
    p1 = p1[p1['status'] == 'ok'].copy()
    p1['sustained'] = p1['passes'].apply(lambda p: p.get('sustained', False))
    sustained = p1[p1['sustained']]
    print(f'Phase 1 sustained: {len(sustained)}')

    p2 = pd.DataFrame([json.loads(l) for l in EXP35_PHASE2.open()])
    p2 = p2[p2['status'] == 'ok'].copy()
    already_done = set(p2['draw_idx'].unique())
    print(f'Already in exp 35 Phase 2: {len(already_done)}')

    extension = sustained[~sustained['draw_idx'].isin(already_done)]
    print(f'Extension set: {len(extension)} draws → '
          f'{len(extension) * P2_SEEDS_PER_DRAW} sims')
    return extension['draw_idx'].tolist()


def combine_and_select():
    sc.heading('COMBINING + SELECTING ROBUST ENSEMBLE')

    p2_old = pd.DataFrame([json.loads(l) for l in EXP35_PHASE2.open()])
    p2_old['source'] = 'exp35_p2'
    p2_new = pd.DataFrame([json.loads(l) for l in EXT_JSONL.open()])
    p2_new['source'] = 'exp36_ext'

    combined = pd.concat([p2_old, p2_new], ignore_index=True)
    combined_ok = combined[combined['status'] == 'ok'].copy()
    print(f'Combined 3-seed records: {len(combined_ok)} (target {545*3} = 1635)')
    combined_ok.to_csv(COMBINED_CSV, index=False)

    numeric = [c for c in combined_ok.columns
               if c not in ('draw_idx','seed','passes','status','source') and
                  pd.api.types.is_numeric_dtype(combined_ok[c])]
    grouped = combined_ok.groupby('draw_idx')[numeric].mean().reset_index()
    for t in ['fsw_band','nontrep_band','trep_band','primary_band','secondary_band',
              'early_lat_band','sustained','hiv_pos_trep_band','hiv_trep_ratio_band']:
        grouped[f'pass_{t}'] = combined_ok.groupby('draw_idx')['passes'].apply(
            lambda s: sum(p.get(t, False) for p in s) / len(s)).reset_index(drop=True)
    grouped['n_pass_mean'] = combined_ok.groupby('draw_idx')['n_pass'].mean().reset_index(drop=True)
    grouped['n_seeds_ok'] = combined_ok.groupby('draw_idx').size().reset_index(drop=True)

    robust = grouped[(grouped['pass_sustained'] == 1.0) & (grouped['n_pass_mean'] >= 5)].copy()
    print(f'\n=== ROBUST ENSEMBLE (sustained 3/3 AND mean n_pass >= 5) ===')
    print(f'  draws: {len(robust)}')

    grouped.to_csv(ROBUST_SUM.with_name('full_summary.csv'), index=False)
    priors = pd.read_csv(EXP35_PRIORS)
    robust_with_priors = priors[priors['draw_idx'].isin(robust['draw_idx'])]
    robust_with_priors = robust_with_priors.merge(robust, on='draw_idx', how='right')
    robust_with_priors.to_csv(ROBUST_CSV, index=False)
    robust.to_csv(ROBUST_SUM, index=False)

    print(f'\n=== ROBUST ENSEMBLE STATS ===')
    for c in ['nontrep_f_2016','trep_f_2016','fsw_prev_2019','hiv_pos_trep_2016',
              'hiv_trep_ratio_2016','primary_share','secondary_share','n_pass_mean']:
        if c in robust.columns:
            print(f'  median {c:30s} = {robust[c].median():.3f}  '
                  f'range [{robust[c].min():.3f}, {robust[c].max():.3f}]')

    sus3 = grouped[grouped['pass_sustained'] == 1.0]
    print(f'\n=== ALL 3/3 SUSTAINED (no n_pass filter) ===')
    print(f'  draws: {len(sus3)}')


def main():
    sc.heading('Exp 36 — Robust ensemble extension')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    extension_idxs = identify_extension_draws()

    priors = pd.read_csv(EXP35_PRIORS)
    tasks = []
    for di in extension_idxs:
        row = priors[priors['draw_idx'] == di].iloc[0].to_dict()
        sim_pars = row_to_sim_pars(row)
        for s_idx in range(P2_SEEDS_PER_DRAW):
            seed = P2_SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di,
                          'sim_pars': sim_pars,
                          'seed': seed,
                          'save_events_as': f'events_{di:04d}_seed{s_idx}.json'})

    run_pool(tasks, EXT_JSONL, 'Extension')
    combine_and_select()


if __name__ == '__main__':
    main()
