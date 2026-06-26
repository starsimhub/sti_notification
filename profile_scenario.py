"""cProfile a single scenario sim to find hot spots.

CELL=SOC|POC|POC_pn|POC_cs|POC_bp  (default SOC)
N_AGENTS=2000 (small for speed)

Top wall-time-consuming functions printed to stdout. Useful to compare
SOC vs POC+PN to attribute the per-sim cost of the layered interventions.
"""
from __future__ import annotations

import cProfile
import os
import pstats
import sys
import time
from pathlib import Path

import pandas as pd

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'calibration' / 'artifacts' / 'scripts'))
sys.path.insert(0, str(HERE))
os.chdir(HERE)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim  # noqa
from interventions import (CondomCounseling, CareSeekScaler,         # noqa
                           PNIntensitySwitch, ANC_PROBS_REALISTIC)
from scenarios import CARE_SEEKING, PN_INTENSITY, BUNDLED_PREVENTION  # noqa
import starsim as ss  # noqa

CELL = os.environ.get('CELL', 'SOC')
N_AGENTS = int(os.environ.get('N_AGENTS', 2000))
N_LIMIT = int(os.environ.get('N_LIMIT', 35))  # top-N to print

# pull draw 263 (rank 1 in exp 06)
draws = pd.read_csv('experiments/06_2026-06-24_kseed_calibration/outputs/draws_used.csv')
row = draws[draws.draw_idx == 263].iloc[0]
sim_pars = row_to_sim_pars(row.to_dict())

# Configure cell
SCENARIO = {
    'SOC':    dict(poc=None, care='baseline', pn='baseline', bp='none'),
    'POC':    dict(poc=True, care='baseline', pn='baseline', bp='none'),
    'POC_cs': dict(poc=True, care='high',     pn='baseline', bp='none'),
    'POC_pn': dict(poc=True, care='baseline', pn='high',     bp='none'),
    'POC_bp': dict(poc=True, care='baseline', pn='baseline', bp='high'),
}
cfg = SCENARIO[CELL]


def build():
    sim = make_sim(seed=263000, start=1985, stop=2040, n_agents=N_AGENTS,
                   poc=cfg['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    extras = []
    csm = CARE_SEEKING[cfg['care']]
    if csm != 1.0:
        extras.append(CareSeekScaler(mult=csm, start=2027))
    if cfg['pn'] != 'baseline':
        pn_int = PN_INTENSITY[cfg['pn']]
        extras.append(PNIntensitySwitch(
            notify_rates=pn_int['notify_rates'],
            attendance_rates=pn_int['attendance_rates'], start=2027))
    if cfg['bp'] != 'none':
        bp = BUNDLED_PREVENTION[cfg['bp']]
        extras.append(CondomCounseling(coverage=bp['coverage'], eff=bp['eff'],
                                       dur=ss.months(bp['dur_months']), start=2027))
    if extras:
        sim.pars['interventions'] = list(sim.pars['interventions']) + extras
    return sim


def main():
    print(f'Profiling CELL={CELL} N_AGENTS={N_AGENTS}', flush=True)
    sim = build()
    t0 = time.time()
    prof = cProfile.Profile()
    prof.enable()
    sim.run()
    prof.disable()
    wall = time.time() - t0
    print(f'\nWall time: {wall:.1f}s')

    print(f'\n=== Top {N_LIMIT} by cumulative time ===')
    pstats.Stats(prof).sort_stats('cumulative').print_stats(N_LIMIT)

    print(f'\n=== Top {N_LIMIT} by total time (self only) ===')
    pstats.Stats(prof).sort_stats('tottime').print_stats(N_LIMIT)


if __name__ == '__main__':
    main()