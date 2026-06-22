"""
Exp 01 — POC etiological testing × elevated PN willingness, pilot run.

10 random draws from calibration/artifacts/draws_used.csv × 3 seeds ×
5 arms = 150 sims. Extracts HIV + syph infections, syph treatments,
notifications & attendances; writes per-(arm, draw, seed) summary
stats to outputs/results.jsonl.

Arms:
  A_soc                : syndromic NG/CT/TV + two-channel syndromic syph + baseline PN
  B_poc_baseline       : POC etiological NG/CT/TV + POC syph (gud2) + baseline PN
  C1_poc_pn_1_5x       : POC etiological NG/CT/TV + POC syph + 1.5x baseline PN
  C2_poc_pn_2x         : POC etiological NG/CT/TV + POC syph + 2.0x baseline PN
  C3_poc_pn_3x         : POC etiological NG/CT/TV + POC syph + 3.0x baseline PN
  D_poc_pn_3x_fsw_out  : C3 stack + direct FSW NG/CT/TV outreach (~70% annual reach)
  E1_d_careseek_1_5x   : D stack + symptomatic care-seeking ×1.5 (F+M, all four STIs incl. syph)
  E2_d_careseek_2x     : D stack + symptomatic care-seeking ×2.0 (F+M, all four STIs incl. syph)
  E3_d_careseek_3x     : D stack + symptomatic care-seeking ×3.0 (F+M; near-ceiling)
The care_seek multiplier scales NG/CT/TV p_symp_care AND the syph
symp_test_prob CSV column simultaneously (the latter is the symptomatic
syph care-seeking rate). ANC pathway is untouched — ANC testing is
opportunistic at the visit, not care-seeking-driven.

POC switch happens at intv_year (2027). In POC arms, syndromic_vds and
syndromic_uds stop at intv_year; the POCPanel takes over for both
sexes; the syph ulcer-channel product swaps to gud2; and POCPN routes
partner-notification attendees through the POC panel + POC syph test
(unconditional on symptoms). All arms run 1985-2040; outcomes counted
over the 2027-2040 post-switch window.
"""
from __future__ import annotations

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
REPO = THIS.parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa


# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------
# Baseline PN rates from interventions.make_pn defaults:
#   notify: stable 0.20, casual 0.10
#   attend: stable F 0.80 / M 0.50; casual F 0.50 / M 0.25
BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}


def scale_pn(mult: float, attend_cap: float = 0.95):
    """Return pn_pars dict with notify+attend rates multiplied by `mult`.
    Attend rates are clamped to attend_cap."""
    notify = {k: v * mult for k, v in BASELINE_NOTIFY.items()}
    attend = {edge: {sex: min(v * mult, attend_cap)
                     for sex, v in sex_rates.items()}
              for edge, sex_rates in BASELINE_ATTEND.items()}
    return {'notify_rates': notify, 'attendance_rates': attend}


ARMS = [
    {'label': 'A_soc',               'poc': False, 'pn_pars': None,           'fsw_outreach': False, 'care_seek_mult': 1.0},
    {'label': 'B_poc_baseline',      'poc': True,  'pn_pars': None,           'fsw_outreach': False, 'care_seek_mult': 1.0},
    {'label': 'C1_poc_pn_1_5x',      'poc': True,  'pn_pars': scale_pn(1.5),  'fsw_outreach': False, 'care_seek_mult': 1.0},
    {'label': 'C2_poc_pn_2x',        'poc': True,  'pn_pars': scale_pn(2.0),  'fsw_outreach': False, 'care_seek_mult': 1.0},
    {'label': 'C3_poc_pn_3x',        'poc': True,  'pn_pars': scale_pn(3.0),  'fsw_outreach': False, 'care_seek_mult': 1.0},
    {'label': 'D_poc_pn_3x_fsw_out', 'poc': True,  'pn_pars': scale_pn(3.0),  'fsw_outreach': True,  'care_seek_mult': 1.0},
    {'label': 'E1_d_careseek_1_5x',  'poc': True,  'pn_pars': scale_pn(3.0),  'fsw_outreach': True,  'care_seek_mult': 1.5},
    {'label': 'E2_d_careseek_2x',    'poc': True,  'pn_pars': scale_pn(3.0),  'fsw_outreach': True,  'care_seek_mult': 2.0},
    {'label': 'E3_d_careseek_3x',    'poc': True,  'pn_pars': scale_pn(3.0),  'fsw_outreach': True,  'care_seek_mult': 3.0},
]


# ---------------------------------------------------------------------------
# Sim construction (overrides _pipeline.build_sim to thread poc + pn_pars)
# ---------------------------------------------------------------------------
def build_sim(seed, sim_pars, poc, pn_pars, fsw_outreach=False,
              care_seek_mult=1.0,
              start=1985, stop=2040, n_agents=10_000):
    """Build a sim. poc=True switches the whole symptomatic care pathway
    to POC etiological at intv_year (2027): NG/CT/TV go through POCPanel
    instead of syndromic_vds/uds; syph ulcer-channel product swaps to
    gud2; partner-notification attendees route through the POC panel +
    POC syph test. fsw_outreach=True adds a periodic POC NG/CT/TV
    screening of currently-active FSW at p=0.10/step (~70% annual).
    care_seek_mult scales NG/CT/TV symptomatic care-seeking (scalar
    applies to both sexes; tuple `(f, m)` scales each sex)."""
    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   poc=poc, pn_pars=pn_pars,
                   fetal_health=False, verbose=-1,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC,
                   fsw_outreach=fsw_outreach,
                   care_seek_mult=care_seek_mult)
    set_pars_local(sim, sim_pars)

    # Apply syph care-seeking multiplier as a MULTIPLIER on top of the
    # post-set_pars_local rel_test (which includes per-draw calibrated
    # rel_test for syph_symp_test). Constructing with rel_test=mult
    # would lose to set_pars_local overwriting it; multiplying here
    # composes the two cleanly.
    if hasattr(care_seek_mult, '__len__'):
        syph_mult = float(care_seek_mult[0])
    else:
        syph_mult = float(care_seek_mult)
    if syph_mult != 1.0:
        # sti.Sim stores interventions in a list pre-init; iterate by
        # name match (same convention as set_pars_local).
        target_names = {'syph_symp_test', 'syph_symp_test_poc',
                        'syph_rash_test'}
        for intv in sim.pars['interventions']:
            if getattr(intv, 'name', None) in target_names:
                intv.pars.rel_test = float(intv.pars.rel_test) * syph_mult

    for mod in sim.pars['diseases']:
        if getattr(mod, 'name', None) == 'syph':
            mod.store_sw = True
            break
    return sim


# ---------------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------------
INTV_YEAR = 2027
END_YEAR  = 2040


def sum_over_window(result, year_lo, year_hi):
    """Sum a result's values over years [year_lo, year_hi]."""
    try:
        years, values = grab_safe(result)
    except Exception:
        return float('nan')
    if years is None:
        return float('nan')
    mask = (years >= year_lo) & (years <= year_hi)
    return float(np.nansum(values[mask]))


def grab_safe(result):
    try:
        years = np.array([t.year + t.month / 12 for t in result.timevec])
        return years, np.array(result.values)
    except Exception:
        return None, None


DISEASE_TX = {'ng': 'ng_tx', 'ct': 'ct_tx', 'tv': 'metronidazole', 'syph': 'syph_tx'}


def extract_endpoints(sim, arm_label, draw_idx, seed):
    """Per-sim summary stats for the 2027-2040 window.

    Endpoints (added 2026-06-11 after pilot review):
      * Per-disease new infections, total (both sexes) and split f/m
      * Per-disease treatment counts: total, successful, unnecessary
      * Per-disease point-prevalence + n_infected at END_YEAR
      * Per-disease % of new infections that were successfully treated
        (a treatment-coverage metric)
      * Syph APO/ABO: new_nnds, new_stillborns, new_congenital,
        new_congenital_deaths (native syph module results — no
        FetalHealth connector needed)
      * PN: notified + attending, current vs prior channel
    """
    rows = {
        'arm': arm_label,
        'draw_idx': int(draw_idx),
        'seed': int(seed),
        'status': 'ok',
    }

    # HIV + STI new infections (overall + by sex)
    rows['hiv_new_inf_2027_2040'] = sum_over_window(
        sim.results['hiv']['new_infections'], INTV_YEAR, END_YEAR)

    for disease in ('syph', 'ng', 'ct', 'tv', 'bv'):
        dres = sim.results[disease]
        rows[f'{disease}_new_inf_2027_2040'] = sum_over_window(
            dres['new_infections'], INTV_YEAR, END_YEAR)
        if 'new_infections_f' in dres:
            rows[f'{disease}_new_inf_f_2027_2040'] = sum_over_window(
                dres['new_infections_f'], INTV_YEAR, END_YEAR)
        if 'new_infections_m' in dres:
            rows[f'{disease}_new_inf_m_2027_2040'] = sum_over_window(
                dres['new_infections_m'], INTV_YEAR, END_YEAR)

        # Point-prevalence + n_infected at END_YEAR
        if 'n_infected' in dres:
            _, vals = grab_safe(dres['n_infected'])
            if vals is not None and len(vals):
                rows[f'{disease}_n_infected_end'] = float(vals[-1])
        if 'prevalence' in dres:
            _, vals = grab_safe(dres['prevalence'])
            if vals is not None and len(vals):
                rows[f'{disease}_prevalence_end'] = float(vals[-1])
        # Syph-specific: sexually_transmissible_prevalence (primary +
        # secondary + early latent). Matches WHO "early infectious
        # syphilis" — the policy-relevant active-transmission slice,
        # rather than the total prev that includes late latent +
        # tertiary (currently not on calibration target).
        if disease == 'syph' and 'sexually_transmissible_prevalence' in dres:
            _, vals = grab_safe(dres['sexually_transmissible_prevalence'])
            if vals is not None and len(vals):
                rows[f'{disease}_sti_prev_end'] = float(vals[-1])

    # Per-disease treatments (total + successful + unnecessary, overall + by sex)
    # Read from sim.results[disease] (per-disease attribution) rather than the
    # intervention's own results, so metronidazole — which treats BOTH TV and BV
    # — gets correctly split between the TV and BV disease tallies (otherwise
    # tv_tx_success would conflate TV and BV cures, inflating apparent TV
    # coverage above 100%).
    for disease, _ in DISEASE_TX.items():
        dres = sim.results.get(disease)
        if dres is None:
            continue
        for key, suffix in (('new_treated',            'tx_total'),
                            ('new_treated_success',    'tx_success'),
                            ('new_treated_unnecessary','tx_unnec')):
            if key in dres:
                rows[f'{disease}_{suffix}_2027_2040'] = sum_over_window(
                    dres[key], INTV_YEAR, END_YEAR)
            for sk in ('f', 'm'):
                k2 = f'{key}_{sk}'
                if k2 in dres:
                    rows[f'{disease}_{suffix}_{sk}_2027_2040'] = sum_over_window(
                        dres[k2], INTV_YEAR, END_YEAR)

        # Coverage proxy: % of new infections successfully treated
        succ = rows.get(f'{disease}_tx_success_2027_2040')
        inf  = rows.get(f'{disease}_new_inf_2027_2040')
        if succ is not None and inf is not None and inf > 0:
            rows[f'{disease}_prop_treated'] = float(succ) / float(inf)
        for sk in ('f', 'm'):
            succ_s = rows.get(f'{disease}_tx_success_{sk}_2027_2040')
            inf_s  = rows.get(f'{disease}_new_inf_{sk}_2027_2040')
            if succ_s is not None and inf_s is not None and inf_s > 0:
                rows[f'{disease}_prop_treated_{sk}'] = float(succ_s) / float(inf_s)

    # Syph APO/ABO (native syph module results — no FetalHealth needed)
    syph_res = sim.results['syph']
    for key, label in (('new_nnds',               'syph_new_nnds_2027_2040'),
                       ('new_stillborns',         'syph_new_stillborns_2027_2040'),
                       ('new_congenital',         'syph_new_congenital_2027_2040'),
                       ('new_congenital_deaths',  'syph_new_congenital_deaths_2027_2040')):
        if key in syph_res:
            rows[label] = sum_over_window(syph_res[key], INTV_YEAR, END_YEAR)

    # PN: notified + attending, current vs prior channel + wasted attendance
    # + false-alarm index (index had no STI at moment of treatment).
    pn = getattr(sim.interventions, 'pn', None)
    if pn is not None:
        for key, label in (('new_notified',          'pn_notified_2027_2040'),
                           ('new_attending',         'pn_attending_2027_2040'),
                           ('new_notified_current',  'pn_notified_current_2027_2040'),
                           ('new_notified_previous', 'pn_notified_previous_2027_2040'),
                           ('new_attended_no_sti',   'pn_attended_no_sti_2027_2040'),
                           ('new_index_no_sti',      'pn_index_no_sti_2027_2040')):
            if key in pn.results:
                rows[label] = sum_over_window(pn.results[key],
                                              INTV_YEAR, END_YEAR)

    # Care-timing analyzer: # of new infections cured within window of
    # acquisition. The denominator is sim.results[d].new_infections in
    # the same window (extracted above as `{disease}_new_inf_2027_2040`).
    # sim.analyzers is a starsim ndict — access by key.
    care_timing = (sim.analyzers.get('care_timing')
                   if hasattr(sim.analyzers, 'get') else None)
    if care_timing is not None:
        # Multi-window: read every {d}_inf_treated_within_{N}mo result
        # the analyzer produces. Default windows are (3, 6) but accept
        # any. Episode treatment rate = treated_within_window / new_inf.
        for d in ('ng', 'ct', 'tv', 'syph'):
            for w in getattr(care_timing, 'windows_months', [3, 6]):
                key = f'{d}_inf_treated_within_{w}mo'
                if key not in care_timing.results:
                    continue
                rows[f'{d}_treated_within_{w}mo_2027_2040'] = sum_over_window(
                    care_timing.results[key], INTV_YEAR, END_YEAR)
                num = rows.get(f'{d}_treated_within_{w}mo_2027_2040')
                den = rows.get(f'{d}_new_inf_2027_2040')
                if num is not None and den is not None and den > 0:
                    rows[f'{d}_prop_treated_{w}mo'] = float(num) / float(den)

    return rows


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
def run_one(task):
    arm = task['arm']
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    seed = task['seed']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars,
                        poc=arm['poc'], pn_pars=arm['pn_pars'],
                        fsw_outreach=arm.get('fsw_outreach', False),
                        care_seek_mult=arm.get('care_seek_mult', 1.0))
        sim.run()
        return extract_endpoints(sim, arm['label'], draw_idx, seed)
    except Exception as e:
        return {'arm': arm['label'], 'draw_idx': int(draw_idx),
                'seed': int(seed),
                'status': f'error: {type(e).__name__}: {e}'}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
HERE = THIS.parent
OUT  = HERE / 'outputs'

N_DRAWS_PILOT = int(os.environ.get('N_DRAWS', 10))
N_SEEDS       = int(os.environ.get('N_SEEDS', 3))
N_WORKERS     = int(os.environ.get('N_WORKERS', 60))
SAMPLE_SEED   = int(os.environ.get('SAMPLE_SEED', 7))
SIM_SEED_BASE = 300_000


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    draws_csv = REPO / 'calibration' / 'artifacts' / 'draws_used.csv'
    draws_full = pd.read_csv(draws_csv)
    rng = np.random.default_rng(SAMPLE_SEED)
    take = rng.choice(len(draws_full), N_DRAWS_PILOT, replace=False)
    draws = draws_full.iloc[sorted(take.tolist())].reset_index(drop=True)
    draws.to_csv(OUT / 'sampled_draws.csv', index=False)
    print(f'Sampled {len(draws)} draws (seed={SAMPLE_SEED}) from {draws_csv}')
    print(f'Arms: {[a["label"] for a in ARMS]}')
    print(f'Total sims: {len(draws) * N_SEEDS * len(ARMS)} '
          f'({len(draws)} draws × {N_SEEDS} seeds × {len(ARMS)} arms)')

    tasks = []
    for _, row in draws.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row.to_dict())
        for s_idx in range(N_SEEDS):
            seed = SIM_SEED_BASE + di * 10 + s_idx
            for arm in ARMS:
                tasks.append({'arm': arm, 'draw_idx': di,
                              'sim_pars': sim_pars, 'seed': seed})

    out_jsonl = OUT / 'results.jsonl'
    t0 = time.time()
    n_ok = n_err = 0
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with out_jsonl.open('w') as fout:
            for i, res in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(res) + '\n')
                fout.flush()
                if res.get('status') == 'ok':
                    n_ok += 1
                else:
                    n_err += 1
                    if n_err <= 10:
                        print(f'  ERROR {res.get("arm")} draw {res.get("draw_idx")}'
                              f' seed {res.get("seed")}: {res.get("status")}',
                              flush=True)
                if i % 25 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    eta = (len(tasks) - i) * elapsed / max(i, 1)
                    print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s '
                          f'eta={eta:.0f}s ok={n_ok} err={n_err}', flush=True)

    print(f'\nDone in {time.time()-t0:.1f}s. ok={n_ok} err={n_err}')
    print(f'Wrote {n_ok + n_err} rows to {out_jsonl}')


if __name__ == '__main__':
    main()
