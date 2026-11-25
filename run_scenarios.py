"""
Scenario driver: SOC reference + POC 3-factor factorial + specificity sweep.

Factors (each a 4-rung ladder in scenarios.py), layered on the POC diagnostic
arm and propagated through the calibrated ensemble:
  - care-seeking         CARE_SEEKING        (CareSeekScaler, NG/CT/TV + BV)
  - partner notification PN_INTENSITY        (PNIntensitySwitch)
  - condom counselling   CONDOM_COUNSELLING  (CondomCounseling coverage)
  - POC specificity      SPEC_SWEEP          (subset of cells only)

Cells:
  SOC                          syndromic dx, all levers baseline (the reference)
  POC_c-{C}_p-{P}_b-{B}        POC dx at BASE_SPEC (98%), 4 x 4 x 4 = 64 cells
                               ("b" = condom counselling; label kept for
                               compatibility with the plotting scripts)
  POC_c-{C}_p-{P}_b-{B}_s-{S}  SPEC_SWEEP_CELLS (6) at each non-base spec (3)
Total 1 + 64 + 18 = 83 cells x N_DRAWS x N_SEEDS sims. One JSON row per
(cell, draw, seed) -> raw_results/scenarios.jsonl.

Run (repo root, `starsim` conda env, multi-core box):
    conda run -n starsim env N_SEEDS=1 N_WORKERS=60 python run_scenarios.py

Quick smoke test (few cells, small pop, 1 draw):
    conda run -n starsim env SMOKE=1 python run_scenarios.py

Prerequisite: DRAWS must point at the ACTIVE calibration baseline (exp 07,
syphilis-free). Override with the DRAWS env var. Endpoints summed over 2027-2040; POC + condom counselling switch
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

from _pipeline import row_to_sim_pars, set_pars_local                 # noqa
from model import make_sim                                            # noqa
from interventions import CondomCounseling, CareSeekScaler, PNIntensitySwitch  # noqa
from scenarios import (CARE_SEEKING, PN_INTENSITY, CONDOM_COUNSELLING,  # noqa
                       BASE_SPEC, SPEC_SWEEP, SPEC_SWEEP_CELLS)

OUT = REPO / 'results'          # small, committable aggregates (kavg CSV)
RAW_OUT = REPO / 'raw_results'  # fat VM-only outputs (jsonl, full TS/snap parquets)
INTV_YEAR = 2027
END_YEAR = 2040
N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))  # match the exp 12 calibration

# Annualised time series we want per (cell, draw, seed).
# Include enough that re-processing (process_results.py) can pick up new metrics
# without re-running the factorial. Keep out of scope: cross-sectional counts
# (n_infected etc.) which have no plotting story.
TS_RESULTS = {
    'hiv':  ['prevalence', 'prevalence_f', 'prevalence_m', 'prevalence_15_49',
             'new_infections',
             'new_diagnoses', 'new_treated'],
    'ng':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections',
             'new_diagnoses', 'new_treated', 'new_treated_success',
             'new_treated_unnecessary'],
    'ct':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections',
             'new_diagnoses', 'new_treated', 'new_treated_success',
             'new_treated_unnecessary'],
    'tv':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections',
             'new_diagnoses', 'new_treated', 'new_treated_success',
             'new_treated_unnecessary'],
}

# Intervention-level TS. Keyed by intervention name lookup on sim.interventions.
INTV_TS_RESULTS = {
    'pn': ['new_notified', 'new_notified_current', 'new_notified_previous',
           'new_notified_no_sti', 'new_attending', 'new_attended_no_sti',
           'new_index_total', 'new_index_no_sti',
           'new_index_total_f', 'new_index_no_sti_f',
           'new_index_total_m', 'new_index_no_sti_m'],
    # True infection status among presenters (sets POC PPV); see
    # analyzers.PresenterEtiology.
    'presenter_etiology': [f'{k}_{ch}_{sx}' for ch in ('care', 'pn')
                           for sx in ('f', 'm')
                           for k in ('n', 'ng', 'ct', 'tv', 'ngct', 'any')],
}
# Age x sex prevalence bases for snapshot years. Auto-discovers
# {base}_{f|m}_{age1}_{age2} variants from the disease's result keys.
SNAPSHOT_BASES = {
    'hiv':  ['prevalence'],
    'ng':   ['prevalence'],
    'ct':   ['prevalence'],
    'tv':   ['prevalence'],
}
SNAPSHOT_YEARS = (2027, 2030, 2035, 2040)

DRAWS_CSV = Path(os.environ.get(
    'DRAWS',
    REPO / 'experiments' / '12_2026-11-25_mix_and_match' / 'outputs' / 'draws_used.csv'))


def build_cells():
    """SOC + POC 4x4x4 factorial at BASE_SPEC + specificity sweep (83 cells)."""
    cells = [dict(label='SOC', poc=None, care='baseline', pn='baseline', bp='none',
                  spec=None)]
    for c in CARE_SEEKING:
        for p in PN_INTENSITY:
            for b in CONDOM_COUNSELLING:
                cells.append(dict(label=f'POC_c-{c}_p-{p}_b-{b}',
                                  poc=True, care=c, pn=p, bp=b, spec=BASE_SPEC))
    for spec in SPEC_SWEEP:
        if spec == BASE_SPEC:
            continue
        for c, p, b in SPEC_SWEEP_CELLS:
            cells.append(dict(label=f'POC_c-{c}_p-{p}_b-{b}_s-{spec:g}',
                              poc=True, care=c, pn=p, bp=b, spec=spec))
    return cells


def build_sim(cell, seed, sim_pars):
    # All sims are built with calibrated-baseline parameters and lever
    # interventions are deferred to intv_year, mirroring how POC / BP
    # activate at 2027 in the user's earlier fix. Without this discipline
    # any scenario lever (CS, PN intensity, BP) baked into construction
    # rewrites history back to 1985 and pre-2027 trajectories diverge
    # across cells.
    #   - care_seek_mult held at 1.0; CareSeekScaler bumps NG/CT/TV/BV
    #     p_symp_care at intv_year
    #   - PN built at baseline rates (matches calibration); PNIntensitySwitch
    #     swaps to the cell's intensity at intv_year
    #   - CondomCounseling already uses start=INTV_YEAR internally
    sim = make_sim(seed=seed, start=1985, stop=END_YEAR, n_agents=N_AGENTS,
                   poc=cell['poc'], pn_pars=PN_INTENSITY['baseline'],
                   poc_spec=None if cell['poc'] is None else cell['spec'],
                   care_seek_mult=1.0,
                   fetal_health=False, verbose=0)
    set_pars_local(sim, sim_pars)
    extra_intvs = []
    csm = CARE_SEEKING[cell['care']]
    if csm != 1.0:
        extra_intvs += CareSeekScaler(mult=csm, start=INTV_YEAR)
    if cell['pn'] != 'baseline':
        pn_int = PN_INTENSITY[cell['pn']]
        extra_intvs.append(PNIntensitySwitch(
            notify_rates=pn_int['notify_rates'],
            attendance_rates=pn_int['attendance_rates'],
            start=INTV_YEAR))
    if cell['bp'] != 'none':
        bp = CONDOM_COUNSELLING[cell['bp']]
        extra_intvs.append(CondomCounseling(coverage=bp['coverage'], eff=bp['eff'],
                                            dur=ss.months(bp['dur_months']),
                                            start=INTV_YEAR))
    if extra_intvs:
        sim.pars['interventions'] = list(sim.pars['interventions']) + extra_intvs
    return sim


def _wsum(res, yv):
    v = np.asarray(res.values)
    m = (yv >= INTV_YEAR) & (yv <= END_YEAR)
    return float(np.nansum(v[m]))


def extract(sim, cell, draw, sub_idx, seed):
    yv = np.floor(np.array([float(t.years) for t in sim.t.timevec]) + 1e-9).astype(int)
    row = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'], bp=cell['bp'],
               poc=bool(cell['poc']), spec=cell['spec'], draw=int(draw),
               sub_idx=int(sub_idx), seed=int(seed), status='ok')
    for d in ('hiv', 'ng', 'ct', 'tv'):
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

    # PN: total + channel split + false-alarm precision endpoints + sex split.
    pn = sim.interventions.get('pn')
    if pn is not None:
        pn_keys = ['new_notified', 'new_attending',
                   'new_notified_current', 'new_notified_previous',
                   'new_index_total', 'new_index_no_sti',
                   'new_notified_no_sti', 'new_attended_no_sti']
        # Sex-stratified versions of the index / notify / attend cascade —
        # VDS (female) vs UDS (male) channels separately so the BV-dominant
        # VDS false-alarm rate isn't averaged away by the male channel.
        for base in ('new_index_total', 'new_index_no_sti',
                     'new_notified', 'new_notified_no_sti',
                     'new_attending', 'new_attended_no_sti'):
            pn_keys += [f'{base}_f', f'{base}_m']
        for k in pn_keys:
            if k in pn.results:
                row[f'pn_{k}'] = _wsum(pn.results[k], yv)

    # Presenter etiology: true infection status among people tested.
    pe = sim.interventions.get('presenter_etiology')
    if pe is not None:
        for k in pe.results.keys():
            if k in ('timevec',):
                continue
            try:
                row[f'pres_{k}'] = _wsum(pe.results[k], yv)
            except Exception:
                pass

    # Care-timing analyzer: # of new infections cured within window of
    # acquisition. Per-disease for NG/CT/TV at the default (3, 6) months.
    care = sim.analyzers.get('care_timing') if hasattr(sim.analyzers, 'get') else None
    if care is not None:
        for d in ('ng', 'ct', 'tv'):
            for w in getattr(care, 'windows_months', (3, 6)):
                key = f'{d}_inf_treated_within_{w}mo'
                if key in care.results:
                    row[f'{d}_treated_within_{w}mo'] = _wsum(care.results[key], yv)
    return row


def _annualize(result):
    """Return (years, values) for an annualised sim result, or (None, None)."""
    try:
        ann = result.resample('year')
        return (np.asarray(ann.timevec.years).astype(int),
                np.asarray(ann.values, dtype=float))
    except Exception:
        return None, None


def extract_timeseries(sim, cell, draw, sub_idx, seed):
    """Annualised TS rows for disease-level + intervention-level metrics."""
    rows = []
    base = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'],
                bp=cell['bp'], poc=bool(cell['poc']), spec=cell['spec'],
                draw=int(draw), sub_idx=int(sub_idx), seed=int(seed))
    # Disease-level TS.
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
    # Intervention-level TS.
    for intv_name, result_names in INTV_TS_RESULTS.items():
        intv = sim.interventions.get(intv_name)
        if intv is None or not hasattr(intv, 'results'):
            continue
        for rname in result_names:
            if rname not in intv.results:
                continue
            years, values = _annualize(intv.results[rname])
            if years is None:
                continue
            for y, v in zip(years, values):
                rows.append({**base,
                             'disease': intv_name, 'result_name': rname,
                             'year': int(y), 'value': float(v)})
    return rows


def extract_snapshots(sim, cell, draw, sub_idx, seed):
    """Age x sex prevalence at SNAPSHOT_YEARS for each SNAPSHOT_BASES entry."""
    rows = []
    base = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'],
                bp=cell['bp'], poc=bool(cell['poc']), spec=cell['spec'],
                draw=int(draw), sub_idx=int(sub_idx), seed=int(seed))
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
        summary = extract(sim, task['cell'], task['draw'], task['sub_idx'], task['seed'])
        ts = extract_timeseries(sim, task['cell'], task['draw'], task['sub_idx'], task['seed'])
        snap = extract_snapshots(sim, task['cell'], task['draw'], task['sub_idx'], task['seed'])
        return {'summary': summary, 'ts': ts, 'snap': snap}
    except Exception as e:
        return {'summary': dict(cell=task['cell']['label'], draw=int(task['draw']),
                                sub_idx=int(task['sub_idx']), seed=int(task['seed']),
                                status=f'error: {type(e).__name__}: {e}'),
                'ts': [], 'snap': []}


def main():
    global N_AGENTS
    smoke = os.environ.get('SMOKE')
    n_seeds = int(os.environ.get('N_SEEDS', 1))
    n_workers = int(os.environ.get('N_WORKERS', 60))
    OUT.mkdir(parents=True, exist_ok=True)
    RAW_OUT.mkdir(parents=True, exist_ok=True)
    if not DRAWS_CSV.exists():
        raise SystemExit(f'draws not found: {DRAWS_CSV} (set DRAWS env var)')
    draws = pd.read_csv(DRAWS_CSV)
    cells = build_cells()
    outfile = RAW_OUT / 'scenarios.jsonl'
    ts_parquet = RAW_OUT / 'scenarios_timeseries.parquet'
    snap_parquet = RAW_OUT / 'scenarios_snapshots.parquet'

    if smoke:
        # Validation run: 5 cells x 5 draws x K=5 seeds = 125 sims.
        # Each lever tested independently against SOC + POC-alone. Used for
        # inspection / plotting after the run lands. At ~7 min/sim on 30
        # workers ~= 30 min wall.
        N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
        keep = {'SOC',
                'POC_c-baseline_p-baseline_b-none',
                'POC_c-high_p-high_b-high',
                'POC_c-baseline_p-baseline_b-none_s-0.95',
                'POC_c-high_p-high_b-high_s-0.995'}
        cells = [c for c in cells if c['label'] in keep]
        draws = draws.head(5)
        n_seeds = 5
        outfile = RAW_OUT / 'scenarios_smoke.jsonl'
        ts_parquet = RAW_OUT / 'scenarios_smoke_timeseries.parquet'
        snap_parquet = RAW_OUT / 'scenarios_smoke_snapshots.parquet'
    else:
        n_draws_env = os.environ.get('N_DRAWS')
        if n_draws_env:
            draws = draws.head(int(n_draws_env))

    # Paired seeds: seed = draw_idx * 1000 + sub_idx, matching the exp 06
    # calibration so the SOC cell at each draw reproduces the calibration's
    # K-seed mean exactly. POC vs SOC contrasts are then paired per draw.
    tasks = []
    for _, r in draws.iterrows():
        di = int(r['draw_idx'])
        sp = row_to_sim_pars(r.to_dict())
        for sub_idx in range(n_seeds):
            seed = di * 1000 + sub_idx
            for cell in cells:
                tasks.append(dict(cell=cell, draw=di, sub_idx=sub_idx,
                                  seed=seed, sim_pars=sp))
    print(f'[scenarios] {len(cells)} cells x {len(draws)} draws x {n_seeds} seeds '
          f'= {len(tasks)} sims | n_agents={N_AGENTS} | draws={DRAWS_CSV.name}'
          f'{" | SMOKE" if smoke else ""}', flush=True)

    t0 = time.time()
    n_ok = n_err = 0
    all_ts, all_snap = [], []
    with mp.Pool(n_workers, maxtasksperchild=10) as pool, outfile.open('w') as f:
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

    # K-seed averaging: per (cell, draw) mean across sub-sims is the unit of
    # signal, mirroring the exp 06 calibration discipline. Raw per-sim
    # scalars stay in {outfile}; the averaged scalars + TS + snapshots are
    # the primary downstream artifacts.
    raw = pd.read_json(outfile, lines=True)
    raw_ok = raw[raw['status'] == 'ok']
    if len(raw_ok):
        meta_cols = ['cell', 'care', 'pn', 'bp', 'poc', 'spec', 'draw']
        scalar_cols = [c for c in raw_ok.columns
                       if c not in meta_cols + ['seed', 'sub_idx', 'status']]
        scalars_avg = raw_ok.groupby(meta_cols, dropna=False)[scalar_cols].mean().reset_index()
        # kavg is small enough to commit; route to OUT (results/) not RAW_OUT.
        scalars_csv = OUT / f'{outfile.stem}.kavg.csv'
        scalars_avg.to_csv(scalars_csv, index=False)
        print(f'  K-avg scalars -> {scalars_csv.name}: {len(scalars_avg)} rows')

    if all_ts:
        ts_df = pd.DataFrame(all_ts)
        ts_avg = (ts_df.groupby(['cell', 'care', 'pn', 'bp', 'poc', 'spec', 'draw',
                                  'disease', 'result_name', 'year'], dropna=False)
                       ['value'].mean().reset_index())
        ts_avg.to_parquet(ts_parquet, index=False)
        print(f'  K-avg ts -> {ts_parquet.name}: {len(ts_avg)} rows '
              f'(from {len(ts_df)} per-sim rows)')
    if all_snap:
        snap_df = pd.DataFrame(all_snap)
        snap_avg = (snap_df.groupby(['cell', 'care', 'pn', 'bp', 'poc', 'spec', 'draw',
                                      'disease', 'result_name', 'sex',
                                      'age_bin', 'year'], dropna=False)
                          ['value'].mean().reset_index())
        snap_avg.to_parquet(snap_parquet, index=False)
        print(f'  K-avg snap -> {snap_parquet.name}: {len(snap_avg)} rows '
              f'(from {len(snap_df)} per-sim rows)')


if __name__ == '__main__':
    main()
