"""
Build a Zimbabwe sim with HIV + 4 discharging STIs (NG/CT/TV/BV) +
syphilis + GUD placeholder. Used to evaluate partner-notification and
care-seeking strategies for STI undertreatment.
"""

import os

import starsim as ss
import sciris as sc
import pandas as pd
import stisim as sti

from interventions import make_testing, make_syph_testing
from hiv_model import make_hiv, make_hiv_intvs
from connectors import sti_fetal

LOCATION = 'zimbabwe'
DATA_DIR = 'data'


def make_discharging_stis():
    ng = sti.Gonorrhea(eff_condom=0.7, beta_m2f=0.12, p_symp=[0.13, 0.65], p_symp_care=[0.49, 0.83])
    ct = sti.Chlamydia(eff_condom=0.8, beta_m2f=0.15, p_symp=[0.30, 0.54], p_symp_care=[0.49, 0.83])
    tv = sti.Trichomoniasis(eff_condom=0.8, beta_m2f=0.14, p_symp=[0.6, 0.5], p_symp_care=[0.49, 0.27])
    bv = sti.BV()
    return ng, ct, tv, bv


def make_ulcerative_stis():
    init_prev_path = f'{DATA_DIR}/init_prev_syph.csv'
    init_prev_latent_path = f'{DATA_DIR}/init_prev_latent_syph.csv'
    syph = sti.Syphilis(
        beta_m2f=0.05,
        beta_m2c=1.,
        eff_condom=0.5,
        rel_trans_latent_half_life=ss.years(1),
        init_prev_data=pd.read_csv(init_prev_path) if os.path.exists(init_prev_path) else None,
        init_prev_latent_data=pd.read_csv(init_prev_latent_path) if os.path.exists(init_prev_latent_path) else None,
    )
    # name='gudp' avoids the buggy `gud_syph` auto-connector match.
    gud = sti.GUDPlaceholder(prevalence=0.01, name='gudp')
    return syph, gud


def make_diseases(which='all'):
    """Build the disease set + matching analyzers. Returns (dict, analyzers)."""
    d = sc.objdict(hiv=make_hiv())
    analyzers = []
    if which in ('discharging', 'all'):
        d.ng, d.ct, d.tv, d.bv = make_discharging_stis()
        analyzers.append(sti.sw_stats(diseases=['ng', 'ct', 'tv']))
    if which in ('ulcerative', 'all'):
        d.syph, d.gudp = make_ulcerative_stis()
    return d, analyzers


def make_networks(dur_recall=ss.years(0.25)):
    sexual = sti.StructuredSexual(
        prop_f0=0.67, prop_m0=0.55,
        prop_f2=0.025, prop_m2=0.05,
        f1_conc=0.05,
        recall_prior=True,
        condom_data=pd.read_csv(f'{DATA_DIR}/condom_use.csv'),
    )
    return [sexual, sti.PriorPartners(dur_recall=dur_recall), ss.MaternalNet()]


def make_interventions(diseases, which='all', poc=None, pn_pars=None, stop=2040):
    intvs = make_hiv_intvs()
    if which in ('discharging', 'all'):
        intvs += make_testing(diseases.ng, diseases.ct, diseases.tv, diseases.bv,
                              poc=poc, pn_pars=pn_pars, stop=stop)
    if which in ('ulcerative', 'all'):
        intvs += make_syph_testing(stop=stop)
    return intvs


def make_sim(seed=1, n_agents=5e3, start=1985, stop=2030,
             pn_pars=None, poc=None, which='all', dur_recall=ss.years(0.25),
             fetal_health=True):

    diseases, analyzers = make_diseases(which)
    networks = make_networks(dur_recall)
    interventions = make_interventions(diseases, which=which, poc=poc, pn_pars=pn_pars, stop=stop)

    # FetalHealth tracks adverse birth outcomes (LBW, SGA, SVN, timing); the
    # sti_fetal connector translates STI infections + treatments into
    # FetalHealth API calls. Both go in `custom` so the standard
    # auto-connector machinery (hiv_*, etc.) still runs.
    custom = [ss.FetalHealth(), sti_fetal()] if fetal_health else None

    simpars = dict(
        rand_seed=seed, n_agents=n_agents,
        start=start, stop=stop,
        use_migration=False, verbose=1/12,
    )
    # Coinfection connectors auto-added by sti.Sim. GUDPlaceholder is named
    # 'gudp' so the buggy `gud_syph` auto-connector isn't matched.
    sim = sti.Sim(
        pars=simpars,
        datafolder=f'{DATA_DIR}/',
        demographics=LOCATION,
        diseases=list(diseases.values()),
        networks=networks,
        interventions=interventions,
        analyzers=analyzers,
        custom=custom,
    )
    return sim


if __name__ == '__main__':
    sim = make_sim(seed=1, which='all', start=1985, stop=1990, n_agents=1000)
    sim.run()
    print(f'Diseases: {list(sim.diseases.keys())}')
    print(f'Connectors: {list(sim.connectors.keys()) if sim.connectors else "none"}')
    print(f'HIV prev (final): {sim.results.hiv.prevalence[-1]:.4f}')
