"""
Create a model with HIV plus 4 co-circulating discharging STIs:
    - chlamydia, gonorrhea, trichomoniasis, and other (BV+)
Used for evaluation of etiological tests compared to syndromic management.
"""

# %% Imports and settings
import starsim as ss
import sciris as sc
import pandas as pd
import stisim as sti

from interventions import make_testing
# from syph_tests import make_syph_testing
from hiv_model import make_hiv, make_hiv_intvs
time_units = dict(unit='month', dt=1)  # Time units for the simulation


def make_discharging_stis(time_units=None):
    ng = sti.Gonorrhea(eff_condom=0.7, beta_m2f=0.12, p_symp=[0.13, 0.65], p_symp_care=[0.49, 0.83], **time_units)
    ct = sti.Chlamydia(eff_condom=0.8, beta_m2f=0.15, p_symp=[0.30, 0.54], p_symp_care=[0.49, 0.83], **time_units)
    tv = sti.Trichomoniasis(eff_condom=0.8, beta_m2f=0.14, p_symp=[0.6, 0.5], p_symp_care=[0.49, 0.27], **time_units)
    bv = sti.SimpleBV(**time_units)
    return ng, ct, tv, bv


def make_ulcerative_stis():
    syph = sti.Syphilis(
        beta_m2f=0.05,  # beta_m2f - use this if using latent logic
        beta_m2c=1.,
        eff_condom=0.5,
        rel_trans_latent_half_life=ss.years(1),
        anc_detection=1.,
        init_prev_data=pd.read_csv('data/init_prev_syph.csv'),
        init_prev_latent_data=pd.read_csv('data/init_prev_latent_syph.csv'),
        **time_units
    )
    gud = sti.GUDPlaceholder(prevalence=0.05, **time_units)

    return syph, gud


def make_sim(seed=1, n_agents=5e3, start=1990, stop=2030, pn_pars=None, poc=None, which='discharging'):

    total_pop = 9980999  # Population of Zimbabwe in 1990

    ####################################################################################################################
    # Demographic modules
    ####################################################################################################################
    fertility_data = pd.read_csv(f'data/asfr.csv')
    pregnancy = ss.Pregnancy(fertility_rate=fertility_data, **time_units)
    death_data = pd.read_csv(f'data/deaths.csv')
    death = ss.Deaths(death_rate=death_data, rate_units=1, **time_units)

    ####################################################################################################################
    # People and networks
    ####################################################################################################################
    ppl = ss.People(n_agents, age_data=pd.read_csv(f'data/age_dist_{start}.csv', index_col='age')['value'])
    sexual = sti.StructuredSexual(
        prop_f0=0.67,
        prop_m0=0.55,
        prop_f2=0.025,
        prop_m2=0.05,
        f1_conc=0.05,
        recall_prior=True,
        condom_data=pd.read_csv(f'data/condom_use.csv'),
        **time_units
    )
    priorpartners = sti.PriorPartners(dur_recall=ss.years(0.25), **time_units)
    maternal = ss.MaternalNet(**time_units)

    ####################################################################################################################
    # Diseases
    ####################################################################################################################
    hiv = make_hiv(time_units)
    diseases = [hiv]
    intvs = make_hiv_intvs(time_units)
    if which == 'discharging':
        ng, ct, tv, bv = make_discharging_stis(time_units)
        diseases += [ng, ct, tv, bv]
        intvs += make_testing(ng, ct, tv, bv, time_units=time_units, poc=poc, pn=pn_pars, stop=stop)
        analyzers = [sti.sw_stats(diseases=['ng', 'ct', 'tv'], **time_units)]
        connectors = [sti.hiv_ng(hiv, ng), sti.hiv_ct(hiv, ct), sti.hiv_tv(hiv, tv)]
    elif which == 'ulcerative':
        raise NotImplementedError("Ulcerative STIs not implemented yet")
        # syph, gud = make_ulcerative_stis()
        # diseases += [syph, gud]
        # intvs += make_syph_testing(scenario='soc', time_units=time_units)
        # connectors = sti.hiv_syph(hiv, syph, rel_sus_hiv_syph=2, **time_units)
        # analyzers = []

    sim = ss.Sim(
        **time_units,
        rand_seed=seed,
        total_pop=total_pop,
        start=ss.date(start),
        stop=ss.date(stop),
        people=ppl,
        diseases=diseases,
        networks=[sexual, priorpartners, maternal],
        demographics=[pregnancy, death],
        interventions=intvs,
        analyzers=analyzers,
        connectors=connectors,
        verbose=1/12,
    )

    return sim


if __name__ == '__main__':

    # SETTINGS
    debug = False
    seed = 1  # 533833
    do_save = True
    do_run = True
    use_calib = True  # Whether to use the calibrated parameters
    which = [
        'discharging',
        'ulcerative',
    ][0]  # Type of STIs to include

    sim = make_sim(seed=seed, which=which, start=1990, stop=2031, pn=True)
    sim.run()
    df = sim.to_df(resample='year', use_years=True, sep='_')  # Use dots to separate columns
    if do_save: sc.saveobj(f'results/sim.df', df)

    # Process and plot
    df = sc.loadobj(f'results/sim.df')
    df.index = df.timevec
    from plot_sims import plot_hiv_sims, plot_sti_sims
    plot_hiv_sims(df, start_year=1990, which='single')
    plot_sti_sims(df, start_year=1990, end_year=2031, fext=which)

