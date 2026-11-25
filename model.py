"""
Build a Zimbabwe sim with HIV + the discharging STIs (NG/CT/TV/BV).

Syphilis was removed from the model in Nov 2026 (exp 07 onward) following
co-author review: the analysis focuses on vaginal/urethral discharge
syndrome management, and syphilis partner management (presumptive partner
treatment, ANC screening, GUD) follows different clinical logic. The last
syphilis-inclusive version is on `main` at commit 8b1f264.
"""

import warnings

import starsim as ss
import starsim.library as ssl
import sciris as sc
import pandas as pd
import stisim as sti

from interventions import make_testing, make_pn
from hiv_model import make_hiv, make_hiv_intvs
from connectors import sti_fetal
from analyzers import CareTimingAnalyzer, PresenterEtiology

LOCATION = 'zimbabwe'
DATA_DIR = 'data'

DISCHARGING = ('ng', 'ct', 'tv')

# Probability that someone with symptoms seeks care, (female, male); BV is female-only.
# CareSeekScaler (interventions.py) scales these from the intervention year.
P_SYMP_CARE = dict(ng=(0.49, 0.83), ct=(0.49, 0.83), tv=(0.49, 0.27), bv=(0.3, 0.3))


def make_discharging_stis(care_seek_mult=1.0):
    """
    Build NG/CT/TV/BV disease modules. ``care_seek_mult`` scales the
    symptomatic care-seeking probability for NG/CT/TV (clipped to [0,1]).
    Scenario runs keep this at 1.0 and use CareSeekScaler instead, so that
    pre-2027 history is identical across cells. Accepts:
      * scalar: applied equally to F and M
      * (mult_f, mult_m) tuple: sex-specific scaling
    """
    if hasattr(care_seek_mult, '__len__'):
        mult_f, mult_m = float(care_seek_mult[0]), float(care_seek_mult[1])
    else:
        mult_f = mult_m = float(care_seek_mult)

    def scaled(care_pair):
        return sti.by_sex(min(1.0, care_pair[0] * mult_f),
                          min(1.0, care_pair[1] * mult_m))

    ng = sti.Gonorrhea(eff_condom=0.7, beta_m2f=0.12, p_symp=sti.by_sex(0.13, 0.65),
                       p_symp_care=scaled(P_SYMP_CARE['ng']))
    ct = sti.Chlamydia(eff_condom=0.8, beta_m2f=0.15, p_symp=sti.by_sex(0.30, 0.54),
                       p_symp_care=scaled(P_SYMP_CARE['ct']))
    tv = sti.Trichomoniasis(eff_condom=0.8, beta_m2f=0.14, p_symp=sti.by_sex(0.6, 0.5),
                            p_symp_care=scaled(P_SYMP_CARE['tv']))
    bv = sti.SimpleBV(p_symp_care=P_SYMP_CARE['bv'][0])
    return ng, ct, tv, bv


def make_diseases(care_seek_mult=1.0, care_timing_windows_months=(3, 6)):
    """Build the disease set + matching analyzers. Returns (dict, analyzers)."""
    d = sc.objdict(hiv=make_hiv())
    d.ng, d.ct, d.tv, d.bv = make_discharging_stis(care_seek_mult=care_seek_mult)
    analyzers = [
        sti.sw_stats(diseases=list(DISCHARGING)),
        CareTimingAnalyzer(
            disease_names=list(DISCHARGING),
            treatment_disease_map={'ng_tx': 'ng', 'ct_tx': 'ct',
                                   'metronidazole': 'tv'},
            windows_months=care_timing_windows_months,
        ),
    ]
    return d, analyzers


def make_networks(dur_recall=ss.years(0.25)):
    sexual = sti.StructuredSexual(
        prop_f0=0.67, prop_m0=0.55,
        prop_f2=0.10, prop_m2=0.20,
        concurrency_dist=ss.nbinom(n=2, p=0.5),
        f1_conc=0.15, m1_conc=0.20,
        f2_conc=1.0, m2_conc=4.4,
        memory=dur_recall,  # Remember partners for dur_recall after a partnership ends (for partner notification)
        condom_data=pd.read_csv(f'{DATA_DIR}/condom_use.csv'),
        fsw_shares=ss.bernoulli(p=0.10),
        client_shares=ss.bernoulli(p=0.20),
        sw_seeking_rate=ss.permonth(20),
    )
    return [sexual, ss.PrenatalNet()]


def make_interventions(poc=None, pn_pars=None, stop=2040,
                       poc_sens=None, poc_spec=None,
                       fsw_outreach=False, fsw_coverage_per_step=0.10,
                       presenter_etiology=True):
    """Orchestrate intervention construction.

    Layout (top to bottom in the returned list):
      1. HIV interventions
      2. NG/CT/TV detection (syndromic VDS/UDS, POC panel) + treatments
      3. PN intervention (from make_pn)

    ``poc_sens`` / ``poc_spec`` override the per-pathogen POC accuracy
    (scalar or {disease: [F, M]}); default is interventions.POC_SENS /
    POC_SPEC.

    ``presenter_etiology`` inserts the PresenterEtiology recorder ahead of
    the detection modules. It records true infection status among people
    presenting for testing (care-seekers and PN attendees): the
    denominator that sets the POC test's PPV and hence the false-positive
    share of index cases.
    """
    intvs = make_hiv_intvs()
    if presenter_etiology:
        intvs.append(PresenterEtiology())
    intvs += make_testing(poc=poc, stop=stop, poc_sens=poc_sens, poc_spec=poc_spec,
                          fsw_outreach=fsw_outreach,
                          fsw_coverage_per_step=fsw_coverage_per_step)
    intvs.append(make_pn(poc=poc, pn_pars=pn_pars))
    return intvs


def make_sim(seed=1, n_agents=5e3, start=1985, stop=2030,
             pn_pars=None, poc=None, poc_sens=None, poc_spec=None,
             dur_recall=ss.years(0.25),
             fetal_health=True, care_seek_mult=1.0, verbose=1/12,
             fsw_outreach=False, fsw_coverage_per_step=0.10,
             presenter_etiology=True, **legacy):
    """Build the Zimbabwe NG/CT/TV/BV + HIV sim.

    Legacy syphilis keyword arguments (``which``, ``poc_syph``,
    ``syph_symp_test_prob``, ``syph_anc_probs``) are accepted and ignored
    with a warning so that older diagnostic scripts still construct.
    """
    if legacy:
        warnings.warn(f'make_sim: ignoring legacy syphilis kwargs {sorted(legacy)} '
                      '(syphilis removed from the model)', stacklevel=2)

    diseases, analyzers = make_diseases(care_seek_mult=care_seek_mult)
    networks = make_networks(dur_recall)
    interventions = make_interventions(poc=poc, pn_pars=pn_pars, stop=stop,
                                       poc_sens=poc_sens, poc_spec=poc_spec,
                                       fsw_outreach=fsw_outreach,
                                       fsw_coverage_per_step=fsw_coverage_per_step,
                                       presenter_etiology=presenter_etiology)

    # FetalHealth tracks adverse birth outcomes; the sti_fetal connector
    # translates NG/CT/TV infections + treatments into FetalHealth API calls.
    custom = [ssl.mnch.FetalHealth(), sti_fetal()] if fetal_health else None

    # The Zimbabwe demographics CSV encodes age-cohort values in thousands,
    # so override total_pop to the actual 1985 population (~8.7M).
    # data/zimbabwe_deaths.csv has AIDS deaths removed (stisim.data.dedup_deaths,
    # anchors 1985 and 2025), since the HIV module kills agents itself; the UN WPP
    # all-cause original is data/zimbabwe_deaths_all_cause.csv.
    simpars = dict(
        rand_seed=seed, n_agents=n_agents,
        start=start, stop=stop,
        use_migration=True, verbose=verbose,
        total_pop=8.7e6,
    )
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
    sim = make_sim(seed=1, start=1985, stop=1990, n_agents=1000)
    sim.run()
    print(f'Diseases: {list(sim.diseases.keys())}')
    print(f'Connectors: {list(sim.connectors.keys()) if sim.connectors else "none"}')
    print(f'HIV prev (final): {sim.results.hiv.prevalence[-1]:.4f}')
