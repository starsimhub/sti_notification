"""
Scenario driver: SOC reference + POC 3-factor full factorial.

Factors (each a 5-rung ladder in scenarios.py), layered on the POC diagnostic
arm and propagated through the calibrated ensemble:
  - care-seeking      CARE_SEEKING       (care_seek_mult on NG/CT/TV p_symp_care)
  - partner notif.    PN_INTENSITY       (pn_pars)
  - bundled prev.     BUNDLED_PREVENTION (CondomCounseling coverage)

Cells:
  SOC                          syndromic dx, all levers baseline (the reference)
  POC_c{C}_p{P}_b{B}           POC dx, 5 x 5 x 5 = 125 cells
                               (c=baseline,p=baseline,b=none is "POC plain")
Total 126 distinct cells x N_DRAWS x N_SEEDS sims. One JSON row per
(cell, draw, seed) -> results/scenarios.jsonl.

Run (repo root, `starsim` conda env, multi-core box):
    conda run -n starsim env N_SEEDS=1 N_WORKERS=60 python run_scenarios.py

Quick smoke test (few cells, small pop, 1 draw):
    conda run -n starsim env SMOKE=1 python run_scenarios.py

Prerequisite: DRAWS must point at the ACTIVE calibration baseline -- NG/CT/TV/
syph all sustaining AND calibrated with the BV-in-VDS model. Override with the
DRAWS env var. Endpoints summed over 2027-2040; POC + bundled prevention switch
on at intv_year (2027).
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import starsim as ss

REPO = Path(__file__).resolve().parent
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
for p in (str(REPO), str(SCRIPTS)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC, CondomCounseling       # noqa
from scenarios import CARE_SEEKING, PN_INTENSITY, BUNDLED_PREVENTION  # noqa

OUT = REPO / 'results'
INTV_YEAR = 2027
END_YEAR = 2040
N_AGENTS = 10_000

# Annualised time series we want per (cell, draw, seed).
TS_RESULTS = {
    'hiv':  ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'ng':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'ct':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'tv':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'syph': ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections',
             'sexually_transmissible_prevalence',
             'sexually_transmissible_prevalence_f',
             'sexually_transmissible_prevalence_m',
             'symptomatic_prevalence', 'primary_prevalence',
             'trep_prevalence_15_64', 'nontrep_prevalence_15_64',
             'new_congenital', 'new_stillborns'],
}
# Age x sex prevalence bases for snapshot years. Auto-discovers
# {base}_{f|m}_{age1}_{age2} variants from the disease's result keys.
SNAPSHOT_BASES = {
    'hiv':  ['prevalence'],
    'ng':   ['prevalence'],
    'ct':   ['prevalence'],
    'tv':   ['prevalence'],
    'syph': ['trep_prevalence', 'nontrep_prevalence',
             'sexually_transmissible_prevalence', 'primary_prevalence'],
}
SNAPSHOT_YEARS = (2027, 2030, 2035, 2040)

DRAWS_CSV = Path(os.environ.get(
    'DRAWS',
    REPO / 'experiments' / '04_2026-06-23_ng_higher_beta_post_treatfix' / 'outputs' / 'draws_used.csv'))


def build_cells():
    """SOC reference + POC 5x5x5 factorial (126 distinct cells)."""
    cells = [dict(label='SOC', poc=None, care='baseline', pn='baseline', bp='none')]
    for c in CARE_SEEKING:
        for p in PN_INTENSITY:
            for b in BUNDLED_PREVENTION:
                cells.append(dict(label=f'POC_c-{c}_p-{p}_b-{b}',
                                  poc=True, care=c, pn=p, bp=b))
    return cells


def build_sim(cell, seed, sim_pars):
    sim = make_sim(seed=seed, start=1985, stop=END_YEAR, n_agents=N_AGENTS,
                   poc=cell['poc'], pn_pars=PN_INTENSITY[cell['pn']],
                   care_seek_mult=CARE_SEEKING[cell['care']],
                   fetal_health=True, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    if cell['bp'] != 'none':
        bp = BUNDLED_PREVENTION[cell['bp']]
        cond = CondomCounseling(coverage=bp['coverage'], eff=bp['eff'],
                                dur=ss.months(bp['dur_months']), start=INTV_YEAR)
        sim.pars['interventions'] = list(sim.pars['interventions']) + [cond]
    return sim


def _wsum(res, yv):
    v = np.asarray(res.values)
    m = (yv >= INTV_YEAR) & (yv <= END_YEAR)
    return float(np.nansum(v[m]))


def extract(sim, cell, draw, seed):
    yv = np.array([t.year for t in sim.t.timevec])
    row = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'], bp=cell['bp'],
               poc=bool(cell['poc']), draw=int(draw), seed=int(seed), status='ok')
    for d in ('hiv', 'ng', 'ct', 'tv', 'syph'):
        dr = sim.results.get(d)
        if dr is None:
            continue
        # Incidence: overall + sex split
        if 'new_infections' in dr:
            row[f'{d}_new_inf'] = _wsum(dr['new_infections'], yv)
        for sk in ('f', 'm'):
            k = f'new_infections_{sk}'
            if k in dr:
                row[f'{d}_new_inf_{sk}'] = _wsum(dr[k], yv)
        # End-of-window point prevalence
        if 'prevalence' in dr:
            row[f'{d}_prev_end'] = float(dr.prevalence.values[-1])
        # Treatments: overall + sex split for total/successful/unnecessary
        for k in ('new_treated', 'new_treated_success', 'new_treated_unnecessary'):
            if k in dr:
                row[f'{d}_{k}'] = _wsum(dr[k], yv)
            for sk in ('f', 'm'):
                k2 = f'{k}_{sk}'
                if k2 in dr:
                    row[f'{d}_{k}_{sk}'] = _wsum(dr[k2], yv)
        # Coverage proxy: % new infections successfully treated
        succ = row.get(f'{d}_new_treated_success')
        inf = row.get(f'{d}_new_inf')
        if succ is not None and inf is not None and inf > 0:
            row[f'{d}_prop_treated'] = float(succ) / float(inf)

    # Syph-specific: sexually-transmissible prevalence (primary + secondary +
    # early latent), the WHO "early infectious syphilis" slice.
    sr = sim.results.get('syph')
    if sr is not None:
        if 'sexually_transmissible_prevalence' in sr:
            row['syph_sti_prev_end'] = float(
                sr['sexually_transmissible_prevalence'].values[-1])
        for k in ('new_nnds', 'new_stillborns', 'new_congenital',
                  'new_congenital_deaths'):
            if k in sr:
                row[f'syph_{k}'] = _wsum(sr[k], yv)

    # PN: total + channel split + false-alarm precision endpoints.
    pn = sim.interventions.get('pn')
    if pn is not None:
        for k in ('new_notified', 'new_attending',
                  'new_notified_current', 'new_notified_previous',
                  'new_index_total', 'new_index_no_sti',
                  'new_notified_no_sti', 'new_attended_no_sti'):
            if k in pn.results:
                row[f'pn_{k}'] = _wsum(pn.results[k], yv)

    # FetalHealth: APO/ABO counts.
    fh = sim.results.get('fetal_health')
    if fh is not None:
        for k in ('n_lbw', 'n_sga', 'n_svn', 'n_births'):
            if k in fh:
                row[f'fh_{k}'] = _wsum(fh[k], yv)

    # Care-timing analyzer: # of new infections cured within window of
    # acquisition. Per-disease for NG/CT/TV/syph at the default (3, 6) months.
    care = sim.analyzers.get('care_timing') if hasattr(sim.analyzers, 'get') else None
    if care is not None:
        for d in ('ng', 'ct', 'tv', 'syph'):
            for w in getattr(care, 'windows_months', (3, 6)):
                key = f'{d}_inf_treated_within_{w}mo'
                if key in care.results:
                    row[f'{d}_treated_within_{w}mo'] = _wsum(care.results[key], yv)
    return row


def _annualize(result):
    """Return (years, values) for an annualised sim result, or (None, None)."""
    try:
        ann = result.annualize()
        return (np.asarray(ann.timevec.years).astype(int),
                np.asarray(ann.values, dtype=float))
    except Exception:
        return None, None


def extract_timeseries(sim, cell, draw, seed):
    """Annualised TS rows for STI prevalences + incidence + key syph variants."""
    rows = []
    base = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'],
                bp=cell['bp'], poc=bool(cell['poc']),
                draw=int(draw), seed=int(seed))
    for disease_name, result_names in TS_RESULTS.items():
        dres = sim.results.get(disease_name)
        if dres is None:
            continue
        for rname in result_names:
            if rname not in dres:
                continue
            years, values = _annualize(dres[rname])
            if years is None:
                continue
            for y, v in zip(years, values):
                rows.append({**base,
                             'disease': disease_name, 'result_name': rname,
                             'year': int(y), 'value': float(v)})
    return rows


def extract_snapshots(sim, cell, draw, seed):
    """Age x sex prevalence at SNAPSHOT_YEARS for each SNAPSHOT_BASES entry."""
    rows = []
    base = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'],
                bp=cell['bp'], poc=bool(cell['poc']),
                draw=int(draw), seed=int(seed))
    for disease_name, bases in SNAPSHOT_BASES.items():
        dres = sim.results.get(disease_name)
        if dres is None:
            continue
        all_keys = list(dres.keys())
        for b in bases:
            prefix = b + '_'
            for key in all_keys:
                if not key.startswith(prefix):
                    continue
                suffix = key[len(prefix):]
                parts = suffix.split('_')
                if len(parts) != 3 or parts[0] not in ('f', 'm'):
                    continue
                try:
                    age1 = int(parts[1]); age2 = int(parts[2])
                except ValueError:
                    continue
                years, values = _annualize(dres[key])
                if years is None:
                    continue
                for snap_year in SNAPSHOT_YEARS:
                    if snap_year not in years:
                        continue
                    idx = int(np.where(years == snap_year)[0][0])
                    rows.append({**base,
                                 'disease': disease_name, 'result_name': b,
                                 'sex': parts[0], 'age_bin': f'{age1}_{age2}',
                                 'year': int(snap_year),
                                 'value': float(values[idx])})
    return rows


def run_one(task):
    try:
        sim = build_sim(task['cell'], task['seed'], task['sim_pars'])
        sim.run()
        summary = extract(sim, task['cell'], task['draw'], task['seed'])
        ts = extract_timeseries(sim, task['cell'], task['draw'], task['seed'])
        snap = extract_snapshots(sim, task['cell'], task['draw'], task['seed'])
        return {'summary': summary, 'ts': ts, 'snap': snap}
    except Exception as e:
        return {'summary': dict(cell=task['cell']['label'], draw=int(task['draw']),
                                seed=int(task['seed']),
                                status=f'error: {type(e).__name__}: {e}'),
                'ts': [], 'snap': []}


def main():
    global N_AGENTS
    smoke = os.environ.get('SMOKE')
    n_seeds = int(os.environ.get('N_SEEDS', 1))
    n_workers = int(os.environ.get('N_WORKERS', 60))
    OUT.mkdir(parents=True, exist_ok=True)
    if not DRAWS_CSV.exists():
        raise SystemExit(f'draws not found: {DRAWS_CSV} (set DRAWS env var)')
    draws = pd.read_csv(DRAWS_CSV)
    cells = build_cells()
    outfile = OUT / 'scenarios.jsonl'
    ts_parquet = OUT / 'scenarios_timeseries.parquet'
    snap_parquet = OUT / 'scenarios_snapshots.parquet'

    if smoke:
        # minimal wiring check: a spanning handful of cells, 1 draw, small pop.
        N_AGENTS = int(os.environ.get('N_AGENTS', 2000))
        keep = {'SOC', 'POC_c-baseline_p-baseline_b-none',
                'POC_c-maximum_p-baseline_b-none',
                'POC_c-baseline_p-maximum_b-none',
                'POC_c-baseline_p-baseline_b-maximum',
                'POC_c-maximum_p-maximum_b-maximum'}
        cells = [c for c in cells if c['label'] in keep]
        draws = draws.head(1)
        n_seeds, n_workers = 1, min(6, n_workers)
        outfile = OUT / 'scenarios_smoke.jsonl'
        ts_parquet = OUT / 'scenarios_smoke_timeseries.parquet'
        snap_parquet = OUT / 'scenarios_smoke_snapshots.parquet'
    else:
        n_draws_env = os.environ.get('N_DRAWS')
        if n_draws_env:
            draws = draws.head(int(n_draws_env))

    tasks = []
    for _, r in draws.iterrows():
        di = int(r['draw_idx'])
        sp = row_to_sim_pars(r.to_dict())
        for s in range(n_seeds):
            for cell in cells:
                tasks.append(dict(cell=cell, draw=di, seed=s, sim_pars=sp))
    print(f'[scenarios] {len(cells)} cells x {len(draws)} draws x {n_seeds} seeds '
          f'= {len(tasks)} sims | n_agents={N_AGENTS} | draws={DRAWS_CSV.name}'
          f'{" | SMOKE" if smoke else ""}', flush=True)

    t0 = time.time()
    n_ok = n_err = 0
    all_ts, all_snap = [], []
    with mp.Pool(n_workers, maxtasksperchild=5) as pool, outfile.open('w') as f:
        for i, payload in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            res = payload['summary']
            f.write(json.dumps(res) + '\n')
            f.flush()
            if res.get('status') == 'ok':
                n_ok += 1
                all_ts.extend(payload['ts'])
                all_snap.extend(payload['snap'])
            else:
                n_err += 1
                if n_err <= 10:
                    print(f'  ERR {res.get("cell")} draw {res.get("draw")}: '
                          f'{res.get("status")}', flush=True)
            if i % 20 == 0 or i == len(tasks):
                el = time.time() - t0
                eta = (len(tasks) - i) * el / max(i, 1)
                print(f'  [{i}/{len(tasks)}] {el:.0f}s eta={eta:.0f}s '
                      f'ok={n_ok} err={n_err}', flush=True)
    print(f'[scenarios] done in {time.time()-t0:.0f}s. ok={n_ok} err={n_err} -> {outfile}')
    if all_ts:
        ts_df = pd.DataFrame(all_ts)
        ts_df.to_parquet(ts_parquet, index=False)
        print(f'  ts -> {ts_parquet.name}: {len(ts_df)} rows')
    if all_snap:
        snap_df = pd.DataFrame(all_snap)
        snap_df.to_parquet(snap_parquet, index=False)
        print(f'  snap -> {snap_parquet.name}: {len(snap_df)} rows')


if __name__ == '__main__':
    main()
