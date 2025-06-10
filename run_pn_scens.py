"""
Run partner notification scenarios
"""
import numpy as np

# %% Imports and settings
import pandas as pd
import sciris as sc
import starsim as ss

# From this repo
from vds_model import make_sim


def make_pn_pars(pnc=None, pnp=None, pac=None, pap=None):
    """
    Make partner notification parameters
    """
    pn_pars = dict(
        p_notify=dict(
            current=ss.bernoulli(p=pnc),  # Probability of notifying current partners
            previous=ss.bernoulli(p=pnp),  # Probability of notifying previous partners
        ),
        p_attends=dict(
            current=ss.bernoulli(p=pac),  # Probability that current partners will attend
            previous=ss.bernoulli(p=pap),  # Probability that previous partners will attend
        ),
    )
    return pn_pars


def run_pn_scens(stop=2040, parallel=True):
    """
    Run analyses
    """
    sc.heading("Making sims... ")

    pndict = sc.objdict()
    pndict['Base'] = None  # No partner notification
    pndict['PN - low'] = make_pn_pars(pnc=0.1, pnp=0, pac=0.1, pap=0)  # Low partner notification
    pndict['PN - med'] = make_pn_pars(pnc=0.2, pnp=0.05, pac=0.2, pap=0.1)  # Medium partner notification
    pndict['PN - high'] = make_pn_pars(pnc=0.5, pnp=0.1, pac=0.5, pap=0.2)  # High partner notification

    sims = sc.autolist()
    for pnlabel, pn_pars in pndict.items():

        for i in range(n_scen_runs):
            printstr = f"Making sim {pnlabel}"
            printstr += f"param set {i+1}/{n_scen_runs}"
            print(printstr)
            sim = make_sim(pn_pars=pn_pars, stop=stop)
            sim.label = f'{pnlabel}--{str(i)}'
            sim.parset = i
            sims += sim

    sc.heading(f"Running {len(sims)} sims... ")
    if parallel:
        sims = ss.parallel(sims).sims
    else:
        for sim in sims:
            sim.run()

    return sims


def process_scens(sims=None):
    """
    Process the scenarios
    """
    if sims is None:
        sims = sc.loadobj('results/pn_scens.obj')

    sc.heading("Processing results...")

    # Make a DataFrame with the results
    df = pd.DataFrame()
    for sim in sims:
        res = sim.results.to_df(resample='year', use_years=True, sep='_')
        res['label'] = sim.label
        res['parset'] = sim.parset
        df = pd.concat([df, res], ignore_index=True)

    # Save the processed results
    sc.saveobj('results/pn_scens_processed.obj', df)
    return df


if __name__ == '__main__':

    # SETTINGS
    debug = False
    seed = 1
    n_scen_runs = [2, 1][debug]  # Number of parameter sets to run per scenario
    to_run = [
        'run_pn_scens',
        'process_scens',  # Process the scenarios
    ]

    if 'run_pn_scens' in to_run:
        # Run analyses
        sims = run_pn_scens(parallel=True, stop=2041)
        sc.saveobj('results/pn_scens.obj', sims)  # Don't commit to repo

    if 'process_scens' in to_run:
        # Process the scenarios
        df = process_scens()
        sc.saveobj('results/pn_scens.df', df)  # Don't commit to repo


        # # Simple plot
        # from utils import set_font
        # set_font(size=30)
        # s_base = sims[0]
        # s_intv = sims[1]
        # import pylab as pl
        # t = s_base.results.ng.timevec
        # fig, axes = pl.subplots(2, 3, figsize=(18, 12))
        # axes = axes.ravel()
        #
        # disease_map = {'ng': 'NG', 'ct': 'CT'}
        # result_map = {
        #     'prevalence': 'Prevalence',
        #     'new_infections': 'Infections',
        #     'n_infected': 'Burden',
        # }
        #
        # pn = 0
        #
        # for dname, dlabel in disease_map.items():
        #     for rname, reslabel in result_map.items():
        #         ax = axes[pn]
        #
        #         r0 = s_base.results[dname][rname].to_df(resample='year', use_years=True, sep='_', col_names=f'{dname}_{rname}')
        #         r1 = s_intv.results[dname][rname].to_df(resample='year', use_years=True, sep='_', col_names=f'{dname}_{rname}')
        #         ax.plot(r0.index, r0, label='Baseline')
        #         ax.plot(r0.index, r1, label='PN')
        #         ax.axvline(x=2027, color='k', ls='--')
        #         ax.set_title(dlabel+' '+reslabel)
        #         if pn == 2: ax.legend(frameon=False, prop={'size': 20})
        #         ax.set_ylim(bottom=0)
        #         ax.set_xlim(left=2020, right=2040)
        #         sc.SIticks(ax=ax)
        #         pn += 1
        #
        # sc.figlayout()
        # sc.savefig("figures/scenarios.png", dpi=100)
        #

    print('Done!')


