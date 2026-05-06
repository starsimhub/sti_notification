"""
Three orthogonal scenario sweeps demonstrating the PN / care-seeking levers.

  Sweep A — PN coverage:    none / low / med / high  (baseline care-seeking, dx=SOC)
  Sweep B — Care-seeking:   1.0× / 1.25× / 1.5× / 2.0×  (PN=med, dx=SOC)
  Sweep C — Dx × PN:        SOC vs POC × 4 PN levels  (baseline care-seeking)

Each cell runs `n_seeds` replicates. Results are extracted to a tidy DataFrame
(one row per (sweep, scenario, seed, year)) and saved to results/sweeps.df.

Default settings give a quick prelim run (~5 min on a laptop). For final
analysis, increase `n_seeds`, `n_agents`, and the simulation period.
"""

import numpy as np
import pandas as pd
import sciris as sc
import starsim as ss

from model import make_sim


# ---------------------------------------------------------------------------
# Scenario library
# ---------------------------------------------------------------------------

PN_LEVELS = sc.objdict(
    none=None,
    low=dict(p_notify_current=ss.bernoulli(p=0.10),
             p_attends_current=ss.bernoulli(p=0.20),
             p_notify_previous=ss.bernoulli(p=0.0),
             p_attends_previous=ss.bernoulli(p=0.0)),
    med=dict(p_notify_current=ss.bernoulli(p=0.30),
             p_attends_current=ss.bernoulli(p=0.40),
             p_notify_previous=ss.bernoulli(p=0.10),
             p_attends_previous=ss.bernoulli(p=0.30)),
    high=dict(p_notify_current=ss.bernoulli(p=0.60),
              p_attends_current=ss.bernoulli(p=0.60),
              p_notify_previous=ss.bernoulli(p=0.30),
              p_attends_previous=ss.bernoulli(p=0.50)),
)


def build_scenarios():
    """Return list of (sweep, scenario, kwargs_for_make_sim) tuples."""
    scenarios = []

    # Sweep A: PN coverage (baseline care-seeking, SOC dx)
    for pn_label, pn_pars in PN_LEVELS.items():
        scenarios.append(('pn_coverage', pn_label,
                          dict(pn_pars=pn_pars, care_seek_mult=1.0, poc=None)))

    # Sweep B: Care-seeking (PN=med, SOC dx)
    for cs_mult in (1.0, 1.25, 1.5, 2.0):
        scenarios.append(('care_seeking', f'cs_x{cs_mult:g}',
                          dict(pn_pars=PN_LEVELS.med, care_seek_mult=cs_mult, poc=None)))

    # Sweep C: Dx × PN
    for dx_label, poc in (('soc', None), ('poc', True)):
        for pn_label, pn_pars in PN_LEVELS.items():
            scenarios.append(('dx_x_pn', f'{dx_label}_{pn_label}',
                              dict(pn_pars=pn_pars, care_seek_mult=1.0, poc=poc)))

    return scenarios


def run_sweeps(n_seeds=3, start=1985, stop=2010, n_agents=2000, parallel=True):
    """
    Build all sims across sweeps × scenarios × seeds, run, and return them.
    """
    sc.heading(f'Building scenarios...')
    scenarios = build_scenarios()
    sims = sc.autolist()
    for sweep, scen, kwargs in scenarios:
        for s in range(n_seeds):
            sim = make_sim(seed=s, start=start, stop=stop, n_agents=n_agents, **kwargs)
            sim.label = f'{sweep}|{scen}|seed={s}'
            sim.sweep = sweep
            sim.scen = scen
            sim.seed = s
            sims.append(sim)

    sc.heading(f'Running {len(sims)} sims (n_seeds={n_seeds}, n_agents={n_agents})...')
    if parallel:
        sims = ss.parallel(sims).sims
    else:
        for sim in sims:
            sim.run()
    return sims


# ---------------------------------------------------------------------------
# Result extraction
# ---------------------------------------------------------------------------

def extract_results(sims):
    """
    Extract a tidy summary DataFrame: one row per (sweep, scen, seed, year).
    Columns: cumulative incidence (NG/CT/TV/syph), HIV new infections,
    notifications, attending, treatments, LBW + SGA + SVN counts.
    """
    rows = []
    for sim in sims:
        yearvec = sim.t.yearvec
        years = np.unique(np.floor(yearvec).astype(int))

        def yearly_sum(arr):
            arr = np.asarray(arr)
            ann = np.zeros(len(years))
            for i, yr in enumerate(years):
                mask = np.floor(yearvec).astype(int) == yr
                ann[i] = arr[mask].sum()
            return ann

        ng_inf = yearly_sum(sim.results.ng.new_infections)
        ct_inf = yearly_sum(sim.results.ct.new_infections)
        tv_inf = yearly_sum(sim.results.tv.new_infections)
        syph_inf = yearly_sum(sim.results.syph.new_infections)
        hiv_inf = yearly_sum(sim.results.hiv.new_infections)

        notif = yearly_sum(sim.results.pn.new_notified) if 'pn' in sim.interventions else np.zeros(len(years))
        attend = yearly_sum(sim.results.pn.new_attending) if 'pn' in sim.interventions else np.zeros(len(years))

        ng_tx = yearly_sum(sim.results.ng_tx.new_treated)
        ct_tx = yearly_sum(sim.results.ct_tx.new_treated)
        mtnz_tx = yearly_sum(sim.results.metronidazole.new_treated)

        if 'fetal_health' in sim.custom:
            fh = sim.results.fetal_health
            lbw = yearly_sum(fh.n_lbw)
            sga = yearly_sum(fh.n_sga)
            svn = yearly_sum(fh.n_svn)
            births = yearly_sum(fh.n_births)
        else:
            lbw = sga = svn = births = np.zeros(len(years))

        for i, yr in enumerate(years):
            rows.append(dict(
                sweep=sim.sweep, scen=sim.scen, seed=sim.seed, year=int(yr),
                ng_inf=ng_inf[i], ct_inf=ct_inf[i], tv_inf=tv_inf[i],
                syph_inf=syph_inf[i], hiv_inf=hiv_inf[i],
                pn_notified=notif[i], pn_attending=attend[i],
                ng_tx=ng_tx[i], ct_tx=ct_tx[i], mtnz_tx=mtnz_tx[i],
                lbw=lbw[i], sga=sga[i], svn=svn[i], births=births[i],
            ))

    return pd.DataFrame(rows)


if __name__ == '__main__':
    debug = False  # quick-run mode
    n_seeds = 1 if debug else 3
    n_agents = 500 if debug else 2000
    stop = 1990 if debug else 2010

    sims = run_sweeps(n_seeds=n_seeds, n_agents=n_agents, stop=stop)
    df = extract_results(sims)

    sc.makepath('results')
    sc.saveobj('results/sweeps.df', df)
    print(df.groupby(['sweep', 'scen']).agg(
        ng_inf=('ng_inf', 'sum'),
        syph_inf=('syph_inf', 'sum'),
        notif=('pn_notified', 'sum'),
        attend=('pn_attending', 'sum'),
        lbw=('lbw', 'sum'),
    ).round(0))
    print('Done.')
