"""
Run partner notification scenarios
"""
import numpy as np

# %% Imports and settings
import pandas as pd
import sciris as sc
import starsim as ss

# From this repo
from model import make_sim


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
            sim = make_sim(seed=i, pn_pars=pn_pars, stop=stop)
            sim.label = f'{pnlabel}--{str(i)}'
            sim.pn_scen = pnlabel  # Label for the scenario
            sim.pn_pars = pn_pars  # Parameters for the scenario
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

    # Make a DataFrame with the results
    sc.heading(f"Processing sims... ")
    dfs = []
    results = ['new_infections', 'new_false_neg', 'n_infected', 'prevalence']
    tx_results = ['new_treated_unnecessary', 'new_treated']
    results = results + tx_results

    for s, sim in enumerate(sims):
        print(f"Processing sim {s+1}/{len(sims)}")
        sdfs = sc.autolist()
        for res in results:
            for disease in ['ng', 'ct', 'tv']:
                colname = f'{disease}.{res}'
                thisdf = sim.results[disease][res].to_df(resample='year', use_years=True, col_names=colname)
                sdfs += thisdf
        for tres in tx_results:
            for tx in ['ng_tx', 'ct_tx', 'metronidazole']:
                colname = f'{tx}.{tres}'
                thisdf = sim.results[tx][tres].to_df(resample='year', use_years=True, col_names=colname)
                sdfs += thisdf

        sdf = pd.concat(sdfs, axis=1)
        sdf['parset'] = sim.parset
        sdf['scenario'] = sim.pn_scen
        dfs += [sdf]

    df = pd.concat(dfs)
    df['timevec'] = df.index

    # Summarize dataframe
    from utils import percentiles
    df_stats = df.groupby(['timevec', 'scenario']).describe(percentiles=percentiles)

    return df_stats


if __name__ == '__main__':

    # SETTINGS
    debug = False
    seed = 1
    n_scen_runs = [20, 1][debug]  # Number of parameter sets to run per scenario
    to_run = [
        'run_pn_scens',
        'process_scens',  # Process the scenarios
        # 'plot_scenarios',  # Plot the scenarios
    ]

    if 'run_pn_scens' in to_run:
        # Run analyses
        sims = run_pn_scens(parallel=True, stop=2041)
        sc.saveobj('results/pn_scens.obj', sims)  # Don't commit to repo

    if 'process_scens' in to_run:
        # Process the scenarios
        df_stats = process_scens()
        sc.saveobj('results/pn_scens.df', df_stats)  # Don't commit to repo

    if 'plot_scenarios' in to_run:
        df = sc.loadobj('results/pn_scens.df')
        from plot_scens import plot_scens
        plot_scens(df, show=False)


    print('Done!')


