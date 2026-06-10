"""
Shared utilities for the calibration pipeline.

Used by run_ensemble.py, extract_summary.py, and reproduce_check.py.
Adapted from experiments/40_final_recalibration/run.py and
experiments/24_concentrated_sustained_handpick/run.py on the
archive/calibration-2026-06 branch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import qmc

# Resolve to the repo root from calibration/artifacts/scripts/
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[3]
DATA_DIR  = REPO_ROOT / 'data'

# Make repo-root modules importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import starsim as ss  # noqa: E402

from model import make_sim                              # noqa: E402
from priors import calib_pars                           # noqa: E402
from interventions import ANC_PROBS_REALISTIC           # noqa: E402

SYMP_TEST_CSV = DATA_DIR / 'symp_test_prob_concentrated.csv'

# Acceptance bands used at calibration time. See methodology.md for
# the rationale; trep_band is relaxed above ZIMPHIA's 2.7% per the
# structural-ceiling diagnosis.
TARGET_BANDS = {
    'fsw_band':            (0.20, 0.40),
    'nontrep_band':        (0.01, 0.05),
    'trep_band':           (0.05, 0.10),
    'primary_band':        (0.45, 0.65),
    'secondary_band':      (0.25, 0.45),
    'hiv_pos_trep_band':   (0.05, 0.09),
    'hiv_trep_ratio_band': (3.0, 6.0),
}
EARLY_LAT_MAX = 0.15


# ---------------------------------------------------------------------------
# Prior sampling and parameter translation
# ---------------------------------------------------------------------------
def generate_prior_draws(n_draws: int, seed: int) -> pd.DataFrame:
    """LHS over the calib_pars space declared in priors.py."""
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


def row_to_sim_pars(row) -> dict:
    """Translate one prior-CSV row into the sim_pars dict that
    `set_pars_local` consumes. log_-prefixed columns are inverse-
    transformed; non-module keys (draw_idx, seed) are dropped."""
    if hasattr(row, 'to_dict'):
        row = row.to_dict()
    sim_pars = {}
    for col, val in row.items():
        if col in ('draw_idx', 'seed'):
            continue
        if isinstance(col, str) and col.startswith('log_'):
            key = col[4:]
            v = float(np.exp(val))
        else:
            key = col
            v = float(val)
        if isinstance(key, str) and '.' in key:
            sim_pars[key] = v
    return sim_pars


def set_pars_local(sim, pars: dict):
    """Apply a `{module.par: value}` dict to a built sim. Handles
    the few priors that need special wiring (lognorm_ex,
    p_symp_primary list-indexing, ss.years for durations)."""
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        found = False
        for category in ('diseases', 'networks', 'interventions',
                         'connectors', 'analyzers',
                         'demographics', 'custom'):
            container = sim.pars.get(category)
            if container is None:
                continue
            if isinstance(container, list):
                for mod in container:
                    if hasattr(mod, 'name') and mod.name == mod_name:
                        if par_name == 'time_to_undetectable':
                            mod.pars[par_name] = ss.lognorm_ex(
                                ss.years(float(value)), ss.years(float(value)))
                        elif par_name == 'rel_trans_latent_half_life':
                            mod.pars[par_name] = ss.years(float(value))
                        elif par_name == 'p_symp_primary_f':
                            mod.pars['p_symp_primary'][0] = float(value)
                        elif par_name == 'p_symp_primary_m':
                            mod.pars['p_symp_primary'][1] = float(value)
                        else:
                            existing = mod.pars.get(par_name)
                            if hasattr(existing, 'set'):
                                existing.set(mean=value)
                            else:
                                mod.pars[par_name] = value
                        found = True
                        break
            if found:
                break
    return sim


# ---------------------------------------------------------------------------
# Sim construction
# ---------------------------------------------------------------------------
def build_sim(seed: int, sim_pars: dict, *,
              start: int = 1985, stop: int = 2040,
              n_agents: int = 10_000,
              pn_pars=None):
    """Construct and parameterise a single sim. Caller runs it."""
    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   pn_pars=pn_pars, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    for mod in sim.pars['diseases']:
        if getattr(mod, 'name', None) == 'syph':
            mod.store_sw = True
            break
    return sim


# ---------------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------------
def grab(r, name):
    """Pull a (years, values) pair from a starsim result by name."""
    res = r[name]
    years = np.array([t.year + t.month / 12 for t in res.timevec])
    return years, np.array(res.values)


def annualize_safe(result):
    """Annualise a starsim result; return (None, None) if it fails."""
    try:
        ann = result.annualize()
        years = np.asarray(ann.timevec.years).astype(int)
        values = np.asarray(ann.values, dtype=float)
        return years, values
    except Exception:
        return None, None


def stage_shares_from_matrix(matrix):
    by_stage = {'primary': 0, 'secondary': 0, 'early_latent': 0,
                'late_latent': 0, 'unknown': 0}
    for (_src, _dst, stage), n in matrix.items():
        by_stage[stage] = by_stage.get(stage, 0) + n
    total = sum(v for k, v in by_stage.items() if k != 'unknown') or 1
    return {k: v / total for k, v in by_stage.items() if k != 'unknown'}


def extract_calibration_summary(sim, draw_idx: int, seed: int) -> dict:
    """Compute per-sim summary stats + pass flags. This is the
    object Phase 1 / Phase 2 write to JSONL for ensemble selection."""
    r = sim.results['syph']
    yrs, prev_f       = grab(r, 'prevalence_f')
    yrs_inf, new_inf  = grab(r, 'new_infections')
    _, fsw_prev       = grab(r, 'prevalence_sw')
    _, client_prev    = grab(r, 'prevalence_client')
    _, nontrep_f      = grab(r, 'nontrep_prevalence_15_64_f')
    _, trep_f         = grab(r, 'trep_prevalence_15_64_f')

    r_trep    = sim.results['syph_hiv_trep']
    r_nontrep = sim.results['syph_hiv_nontrep']
    yrs_ana, trep_has_hiv = grab(r_trep, 'syph_prev_has_hiv')
    _, trep_no_hiv        = grab(r_trep, 'syph_prev_no_hiv')
    _, nontrep_has_hiv    = grab(r_nontrep, 'syph_prev_has_hiv')
    _, nontrep_no_hiv     = grab(r_nontrep, 'syph_prev_no_hiv')
    _, hiv_prev           = grab(sim.results['hiv'], 'prevalence')

    def at(arr, ys, year):
        i = np.argmin(np.abs(ys - year))
        return float(arr[i])

    def avg(arr, ys, y1, y2):
        m = (ys >= y1) & (ys < y2)
        return float(np.nanmean(arr[m])) if m.any() else float('nan')

    ana = getattr(sim.analyzers, 'syph_transmission_events', None)
    matrix = dict(ana.matrix) if ana is not None else {}
    plateau_shares = stage_shares_from_matrix(matrix)

    fsw_v    = at(fsw_prev,  yrs, 2019)
    ntr_v    = at(nontrep_f, yrs, 2016)
    tr_v     = at(trep_f,    yrs, 2016)
    prim_v   = plateau_shares.get('primary',      0.0)
    sec_v    = plateau_shares.get('secondary',    0.0)
    el_v     = plateau_shares.get('early_latent', 0.0)
    ll_v     = plateau_shares.get('late_latent',  0.0)
    ni_late  = avg(new_inf, yrs_inf, 2030, 2040)
    pf_late  = avg(prev_f,  yrs, 2035, 2040)
    sustained = bool(ni_late > 0 and pf_late >= 0.001)

    hiv_pos_trep    = at(trep_has_hiv,    yrs_ana, 2016)
    hiv_neg_trep    = at(trep_no_hiv,     yrs_ana, 2016)
    hiv_pos_nontrep = at(nontrep_has_hiv, yrs_ana, 2016)
    hiv_neg_nontrep = at(nontrep_no_hiv,  yrs_ana, 2016)
    hiv_trep_ratio  = (hiv_pos_trep / hiv_neg_trep) if hiv_neg_trep > 0 else float('nan')

    passes = {
        'fsw_band':            TARGET_BANDS['fsw_band'][0]     <= fsw_v <= TARGET_BANDS['fsw_band'][1],
        'nontrep_band':        TARGET_BANDS['nontrep_band'][0] <= ntr_v <= TARGET_BANDS['nontrep_band'][1],
        'trep_band':           TARGET_BANDS['trep_band'][0]    <= tr_v  <= TARGET_BANDS['trep_band'][1],
        'primary_band':        TARGET_BANDS['primary_band'][0]   <= prim_v <= TARGET_BANDS['primary_band'][1],
        'secondary_band':      TARGET_BANDS['secondary_band'][0] <= sec_v  <= TARGET_BANDS['secondary_band'][1],
        'early_lat_band':      el_v <= EARLY_LAT_MAX,
        'sustained':           sustained,
        'hiv_pos_trep_band':   TARGET_BANDS['hiv_pos_trep_band'][0]  <= hiv_pos_trep <= TARGET_BANDS['hiv_pos_trep_band'][1],
        'hiv_trep_ratio_band': (not np.isnan(hiv_trep_ratio))
                                and TARGET_BANDS['hiv_trep_ratio_band'][0] <= hiv_trep_ratio
                                                                       <= TARGET_BANDS['hiv_trep_ratio_band'][1],
    }
    n_pass = sum(passes.values())

    return {
        'draw_idx': draw_idx, 'seed': seed,
        'fsw_prev_2019':                fsw_v,
        'nontrep_f_2016':               ntr_v,
        'trep_f_2016':                  tr_v,
        'primary_share':                prim_v,
        'secondary_share':              sec_v,
        'early_lat_share':              el_v,
        'late_lat_share':               ll_v,
        'client_prev_2016':             at(client_prev, yrs, 2016),
        'overall_prev_f_2035_2040_mean': pf_late,
        'new_inf_2030_2040_mean':       ni_late,
        'hiv_pos_trep_2016':            hiv_pos_trep,
        'hiv_neg_trep_2016':            hiv_neg_trep,
        'hiv_pos_nontrep_2016':         hiv_pos_nontrep,
        'hiv_neg_nontrep_2016':         hiv_neg_nontrep,
        'hiv_trep_ratio_2016':          float(hiv_trep_ratio) if not np.isnan(hiv_trep_ratio) else None,
        'hiv_prev_2010_2020':           avg(hiv_prev, yrs, 2010, 2020),
        'passes':                       passes,
        'n_pass':                       int(n_pass),
        'status':                       'ok',
    }


# ---------------------------------------------------------------------------
# Time-series and snapshot extraction (used by extract_summary.py)
# ---------------------------------------------------------------------------
TIME_SERIES_RESULTS = {
    'hiv':  ['prevalence', 'prevalence_15_49',
             'prevalence_f', 'prevalence_m', 'new_infections'],
    'ng':   ['prevalence', 'prevalence_f', 'prevalence_m',
             'prevalence_f_25_30', 'new_infections'],
    'ct':   ['prevalence', 'prevalence_f', 'prevalence_m',
             'prevalence_f_25_30', 'new_infections'],
    'tv':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'syph': [
        'new_infections',
        'prevalence', 'prevalence_f', 'prevalence_m',
        'prevalence_sw', 'prevalence_client',
        'trep_prevalence_15_64',
        'trep_prevalence_15_64_f', 'trep_prevalence_15_64_m',
        'nontrep_prevalence_15_64',
        'nontrep_prevalence_15_64_f', 'nontrep_prevalence_15_64_m',
        'active_prevalence', 'active_prevalence_f', 'active_prevalence_m',
        'sexually_transmissible_prevalence',
        'sexually_transmissible_prevalence_f',
        'sexually_transmissible_prevalence_m',
        'symptomatic_prevalence',
        'symptomatic_prevalence_f', 'symptomatic_prevalence_m',
        'primary_prevalence',
        'primary_prevalence_f', 'primary_prevalence_m',
    ],
}

SNAPSHOT_BASES = {
    'hiv':  ['prevalence'],
    'ng':   ['prevalence'],
    'ct':   ['prevalence'],
    'tv':   ['prevalence'],
    'syph': ['trep_prevalence', 'nontrep_prevalence',
             'active_prevalence', 'sexually_transmissible_prevalence',
             'symptomatic_prevalence', 'primary_prevalence'],
}

SNAPSHOT_YEARS = (2016, 2020)


def extract_time_series(sim, draw_idx: int, seed: int) -> list:
    """Return annualised time series rows for all configured diseases."""
    rows = []
    for disease_name, result_names in TIME_SERIES_RESULTS.items():
        disease_results = sim.results.get(disease_name)
        if disease_results is None:
            continue
        for rname in result_names:
            if rname not in disease_results:
                continue
            years, values = annualize_safe(disease_results[rname])
            if years is None:
                continue
            for y, v in zip(years, values):
                rows.append({
                    'draw_idx': int(draw_idx), 'seed': int(seed),
                    'disease': disease_name, 'result_name': rname,
                    'year': int(y), 'value': float(v),
                })
    return rows


def extract_snapshots(sim, draw_idx: int, seed: int) -> list:
    """Return 2016/2020 age×sex snapshot rows."""
    rows = []
    for disease_name, bases in SNAPSHOT_BASES.items():
        disease_results = sim.results.get(disease_name)
        if disease_results is None:
            continue
        all_keys = list(disease_results.keys())
        for base in bases:
            prefix = base + '_'
            for key in all_keys:
                if not key.startswith(prefix):
                    continue
                suffix = key[len(prefix):]
                parts = suffix.split('_')
                if len(parts) != 3 or parts[0] not in ('f', 'm'):
                    continue
                try:
                    age1 = int(parts[1])
                    age2 = int(parts[2])
                except ValueError:
                    continue
                years, values = annualize_safe(disease_results[key])
                if years is None:
                    continue
                for snap_year in SNAPSHOT_YEARS:
                    if snap_year not in years:
                        continue
                    idx = int(np.where(years == snap_year)[0][0])
                    rows.append({
                        'draw_idx': int(draw_idx), 'seed': int(seed),
                        'disease': disease_name, 'result_name': base,
                        'sex': parts[0], 'age_bin': f'{age1}_{age2}',
                        'year': int(snap_year),
                        'value': float(values[idx]),
                    })
    return rows


# ---------------------------------------------------------------------------
# Quantile aggregation
# ---------------------------------------------------------------------------
def compute_ts_quantiles(ts_df: pd.DataFrame) -> pd.DataFrame:
    return (ts_df.groupby(['disease', 'result_name', 'year'])['value']
            .agg(median='median',
                 ci80_lo=lambda s: np.quantile(s, 0.10),
                 ci80_hi=lambda s: np.quantile(s, 0.90),
                 ci95_lo=lambda s: np.quantile(s, 0.025),
                 ci95_hi=lambda s: np.quantile(s, 0.975),
                 mean='mean',
                 n='count')
            .reset_index())


def compute_snap_quantiles(snap_df: pd.DataFrame) -> pd.DataFrame:
    return (snap_df.groupby(['disease', 'result_name', 'year',
                             'sex', 'age_bin'])['value']
            .agg(median='median',
                 ci80_lo=lambda s: np.quantile(s, 0.10),
                 ci80_hi=lambda s: np.quantile(s, 0.90),
                 ci95_lo=lambda s: np.quantile(s, 0.025),
                 ci95_hi=lambda s: np.quantile(s, 0.975),
                 mean='mean',
                 n='count')
            .reset_index())
