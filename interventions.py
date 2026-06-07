"""
Custom interventions for the discharge valuation
"""

import stisim as sti
import starsim as ss
import numpy as np
import pandas as pd
import sciris as sc
from collections import defaultdict


class SyndromicMgmt(sti.STITest):
    def __init__(self, pars=None, treatments=None, diseases=None, outcome_treatment_map=None, treat_prob_data=None, years=None, start=None, stop=None, eligibility=None, name=None, label=None, **kwargs):
        super().__init__(years=years, start=start, stop=stop, eligibility=eligibility, name=name, label=label)
        self.define_pars(
            tx_mix_cerv = dict(
                all3=[0.50, 0.10],
                ngct=[0.20, 0.80],
                mtnz=[0.15, 0.00],
                none=[0.15, 0.10],
            ),
            tx_mix_noncerv = dict(
                all3=[0.40, 0.10],
                ngct=[0.10, 0.80],
                mtnz=[0.25, 0.00],
                none=[0.25, 0.10],
            ),
            tx_cerv_f=ss.choice(a=4),
            tx_cerv_m=ss.choice(a=4),
            tx_noncerv_f=ss.choice(a=4),
            tx_noncerv_m=ss.choice(a=4),
            record_results=False,  # Very slow to record results!
            dt_scale=False,
        )
        self.update_pars(pars, **kwargs)
        self.fvals_cerv = [v[0] for v in self.pars.tx_mix_cerv.values()]
        self.mvals_cerv = [v[1] for v in self.pars.tx_mix_cerv.values()]
        self.fvals_noncerv = [v[0] for v in self.pars.tx_mix_noncerv.values()]
        self.mvals_noncerv = [v[1] for v in self.pars.tx_mix_noncerv.values()]

        # Store treatments and diseases
        self.treatments = sc.tolist(treatments)
        self.diseases = diseases
        if outcome_treatment_map is None:
            outcome_treatment_map = dict(
                all3=self.treatments,
                ngct=[self.treatments[0], self.treatments[1]],
                mtnz=[self.treatments[1]],
                none=[],
            )
        self.outcome_treatment_map = outcome_treatment_map

        self.define_states(
            ss.FloatArr('ti_referred'),
            ss.FloatArr('ti_dismissed'),
        )
        self.treat_prob_data = treat_prob_data
        self.treat_prob = None
        self.treated_by_uid = None

        # Interim results
        self.sti_results = sc.objdict()
        if self.pars.record_results:
            self.sti_results = sc.objdict(
                new_ng_only=0,
                new_ct_only=0,
                new_tv_only=0,
                new_bv_only=0,
                new_ng_ct=0,
                new_ng_tv=0,
                new_ng_bv=0,
                new_ct_tv=0,
                new_ct_bv=0,
                new_tv_bv=0,
                new_ng_ct_tv=0,
                new_ng_ct_bv=0,
                new_ng_tv_bv=0,
                new_ct_tv_bv=0,
                new_ng_ct_tv_bv=0,
                new_all_ng=0,
                new_all_ct=0,
                new_all_tv=0,
                new_all_bv=0,
            )
            for k in self.sti_results.keys():
                self.sti_results[k+'_f'] = 0
                self.sti_results[k+'_m'] = 0

        return

    def init_pre(self, sim):
        super().init_pre(sim)
        self.pars.tx_cerv_f.set(p=self.fvals_cerv)
        self.pars.tx_cerv_m.set(p=self.mvals_cerv)
        self.pars.tx_noncerv_f.set(p=self.fvals_noncerv)
        self.pars.tx_noncerv_m.set(p=self.mvals_noncerv)
        return

    def init_results(self):
        super().init_results()
        results = sc.autolist()
        sexkeys = ['', 'f', 'm']
        for sk in sexkeys:
            skk = '' if sk == '' else f'_{sk}'
            skl = '' if sk == '' else f' - {sk.upper()}'
            results += [
                ss.Result('new_care_seekers'+skk, dtype=int, label="Care seekers"+skl),
                ss.Result('new_tx0'+skk, dtype=int, label="No treatment"+skl),
                ss.Result('new_tx1'+skk, dtype=int, label="1 treatment"+skl),
                ss.Result('new_tx2'+skk, dtype=int, label="2 treatment"+skl),
                ss.Result('new_tx3'+skk, dtype=int, label="3 treatments"+skl),
                ss.Result('new_sti1'+skk, dtype=int, label='1 STI'+skl),
                ss.Result('new_sti2'+skk, dtype=int, label='2 STIs'+skl),
                ss.Result('new_sti3'+skk, dtype=int, label='3 STIs'+skl),
                ss.Result('new_sti4'+skk, dtype=int, label='4 STIs'+skl),
            ]
        self.define_results(*results)
        return

    def step(self, uids=None):
        sim = self.sim
        ppl = sim.people
        self.treated_by_uid = None

        # If this intervention has stopped, reset eligibility for all associated treatments
        if self.t.now('year') >= self.stop:
            for treatment in self.treatments:
                treatment.eligibility = ss.uids()  # Reset
            return

        if self.t.now('year') >= self.start:

            if uids is None:
                uids = self.check_eligibility()
                self.ti_tested[uids] = self.ti

            if len(uids):
                f_uids = uids[sim.people.female[uids]]
                m_uids = uids[sim.people.male[uids]]

                # Determine who has symptomatic cervical infection
                is_cerv = sim.people.ng.symptomatic | sim.people.ct.symptomatic

                # Determine treatment outcome for each agent
                f_cerv_uids = f_uids[is_cerv[f_uids]]  # UIDs of women with cervical infection
                f_noncerv_uids = f_uids[~is_cerv[f_uids]]  # UIDs of women without cervical infection

                ofc = self.pars.tx_cerv_f.rvs(f_cerv_uids)
                ofnc = self.pars.tx_noncerv_f.rvs(f_noncerv_uids)
                om = self.pars.tx_cerv_m.rvs(m_uids)

                # Treatment outcomes
                outcomes = dict(
                    all3=f_cerv_uids[ofc == 0] | f_noncerv_uids[ofnc == 0] | m_uids[om == 0],
                    ngct=f_cerv_uids[ofc == 1] | f_noncerv_uids[ofnc == 1] | m_uids[om == 1],
                    mtnz=f_cerv_uids[ofc == 2] | f_noncerv_uids[ofnc == 2] | m_uids[om == 2],
                    none=f_cerv_uids[ofc == 3] | f_noncerv_uids[ofnc == 3] | m_uids[om == 3],
                )

                # Figure out missed diagnoses
                if self.pars.record_results:
                    for disease in self.diseases:
                        for pkey, pattr in disease.sex_keys.items():
                            skk = '' if pkey == '' else f'_{pkey}'

                            disease.results[f'new_true_pos{skk}'][self.ti] += len(outcomes['all3'] & disease.treatable & ppl[pattr])
                            disease.results[f'new_false_pos{skk}'][self.ti] += len(outcomes['all3'] & disease.susceptible & ppl[pattr])
                            disease.results[f'new_true_neg{skk}'][self.ti] += len(outcomes['none'] & disease.susceptible & ppl[pattr])
                            disease.results[f'new_false_neg{skk}'][self.ti] += len(outcomes['none'] & disease.treatable & ppl[pattr])

                    # Additional cervical
                    for disease in [self.sim.diseases.ng, self.sim.diseases.ct]:
                        for pkey, pattr in disease.sex_keys.items():
                            skk = '' if pkey == '' else f'_{pkey}'
                            disease.results[f'new_true_pos{skk}'][self.ti] += len(outcomes['ngct'] & disease.treatable & ppl[pattr])
                            disease.results[f'new_false_pos{skk}'][self.ti] += len(outcomes['ngct'] & disease.susceptible & ppl[pattr])
                            disease.results[f'new_false_neg{skk}'][self.ti] += len(outcomes['mtnz'] & disease.treatable & ppl[pattr])
                            disease.results[f'new_true_neg{skk}'][self.ti] += len(outcomes['mtnz'] & disease.susceptible & ppl[pattr])

                    for disease in [self.sim.diseases.tv]:
                        for pkey, pattr in disease.sex_keys.items():
                            skk = '' if pkey == '' else f'_{pkey}'
                            disease.results[f'new_true_pos{skk}'][self.ti] += len(outcomes['mtnz'] & disease.treatable & ppl[pattr])
                            disease.results[f'new_false_pos{skk}'][self.ti] += len(outcomes['mtnz'] & disease.susceptible & ppl[pattr])
                            disease.results[f'new_false_neg{skk}'][self.ti] += len(outcomes['ngct'] & disease.treatable & ppl[pattr])
                            disease.results[f'new_true_neg{skk}'][self.ti] += len(outcomes['ngct'] & disease.susceptible & ppl[pattr])

                # Update treatment eligibility
                for outcome, txs in self.outcome_treatment_map.items():
                    for tx in txs:
                        tx.eligibility = tx.eligibility | outcomes[outcome]

                # Update states: time referred to treatment for anyone referred
                referred_uids = outcomes['all3'] | outcomes['ngct'] | outcomes['mtnz']
                dismissed_uids = outcomes['none']
                self.ti_referred[referred_uids] = self.ti
                self.ti_dismissed[dismissed_uids] = self.ti
                self.treated_by_uid = outcomes

            if self.pars.record_results:
                self.store_results()

            return

    def store_results(self):
        """
        This has a different name to the usual update_results method because we want to ensure
        that it is called BEFORE the treatments are applied, so that we record who was infected.
        """
        ti = self.ti
        ppl = self.sim.people
        just_tested = self.ti_tested == ti
        self.results['new_care_seekers'][ti] += sti.count(just_tested)
        self.results['new_care_seekers_f'][ti] += sti.count(just_tested & ppl.female)
        self.results['new_care_seekers_m'][ti] += sti.count(just_tested & ppl.male)

        # Record the number of people who received 0-3 treatments
        sexdict = {'': 'alive', 'f': 'female', 'm': 'male'}
        if self.treated_by_uid is not None:
            for sk, sl in sexdict.items():
                skk = '' if sk == '' else f'_{sk}'
                self.results['new_tx0'+skk][ti] += sti.count(ppl[sl][self.treated_by_uid['none']])
                self.results['new_tx1'+skk][ti] += sti.count(ppl[sl][self.treated_by_uid['mtnz']])
                self.results['new_tx2'+skk][ti] += sti.count(ppl[sl][self.treated_by_uid['ngct']])
                self.results['new_tx3'+skk][ti] += sti.count(ppl[sl][self.treated_by_uid['all3']])

        # Record
        for sk, sl in sexdict.items():
            skk = '' if sk == '' else f'_{sk}'

            self.sti_results['new_ng_only'+skk] = len((just_tested & ppl.ng.infected & ~ppl.ct.infected & ~ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ct_only'+skk] = len((just_tested & ~ppl.ng.infected & ppl.ct.infected & ~ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_tv_only'+skk] = len((just_tested & ~ppl.ng.infected & ~ppl.ct.infected & ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_bv_only'+skk] = len((just_tested & ~ppl.ng.infected & ~ppl.ct.infected & ~ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)

            self.sti_results['new_ng_ct'+skk] = len((just_tested & ppl.ng.infected & ppl.ct.infected & ~ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ng_tv'+skk] = len((just_tested & ppl.ng.infected & ~ppl.ct.infected & ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ng_bv'+skk] = len((just_tested & ppl.ng.infected & ~ppl.ct.infected & ~ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ct_tv'+skk] = len((just_tested & ~ppl.ng.infected & ppl.ct.infected & ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ct_bv'+skk] = len((just_tested & ~ppl.ng.infected & ppl.ct.infected & ~ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_tv_bv'+skk] = len((just_tested & ~ppl.ng.infected & ~ppl.ct.infected & ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)

            self.sti_results['new_ng_ct_tv'+skk] = len((just_tested & ppl.ng.infected & ppl.ct.infected & ppl.tv.infected & ~ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ng_ct_bv'+skk] = len((just_tested & ppl.ng.infected & ppl.ct.infected & ~ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ng_tv_bv'+skk] = len((just_tested & ppl.ng.infected & ~ppl.ct.infected & ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)
            self.sti_results['new_ct_tv_bv'+skk] = len((just_tested & ~ppl.ng.infected & ppl.ct.infected & ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)

            self.sti_results['new_ng_ct_tv_bv'+skk] = len((just_tested & ppl.ng.infected & ppl.ct.infected & ppl.tv.infected & ppl.bv.infected & ppl[sl]).uids)

            self.sti_results['new_all_ng'+skk] = len((just_tested & ppl.ng.infected & ppl[sl]).uids)
            self.sti_results['new_all_ct'+skk] = len((just_tested & ppl.ct.infected & ppl[sl]).uids)
            self.sti_results['new_all_tv'+skk] = len((just_tested & ppl.tv.infected & ppl[sl]).uids)
            self.sti_results['new_all_bv'+skk] = len((just_tested & ppl.bv.infected & ppl[sl]).uids)

            self.results['new_sti1'+skk][ti] = (self.sti_results['new_ng_only'+skk] +
                                                self.sti_results['new_ct_only'+skk] +
                                                self.sti_results['new_tv_only'+skk] +
                                                self.sti_results['new_bv_only'+skk])
            self.results['new_sti2'+skk][ti] = (self.sti_results['new_ng_ct'+skk] +
                                            self.sti_results['new_ng_tv'+skk] +
                                            self.sti_results['new_ng_bv'+skk] +
                                            self.sti_results['new_ct_tv'+skk] +
                                            self.sti_results['new_ct_bv'+skk] +
                                            self.sti_results['new_tv_bv'+skk])
            self.results['new_sti3'+skk][ti] = (self.sti_results['new_ng_ct_tv'+skk] +
                                            self.sti_results['new_ng_ct_bv'+skk] +
                                            self.sti_results['new_ng_tv_bv'+skk] +
                                            self.sti_results['new_ct_tv_bv'+skk])

            self.results['new_sti4'+skk][ti] = self.sti_results['new_ng_ct_tv_bv'+skk]

        return


class SyndromicPN(sti.PartnerNotification):
    """
    Partner notification adapted for syndromic STI treatment.

    Inherits the network-based traceback (current sexual network + optional
    PriorPartners recall) and notification × attendance logic from
    :class:`stisim.PartnerNotification`. On attendance, routes partners by
    sex through the appropriate syndromic-management intervention; partners
    are treated per the syndromic algorithm on the next timestep.

    Args:
        eligibility: Index-case selector, e.g. just-treated agents.
        syndromic_vds: SyndromicMgmt instance for women.
        syndromic_uds: SyndromicMgmt instance for men.
    """
    def __init__(self, eligibility, syndromic_vds, syndromic_uds, **kwargs):
        super().__init__(eligibility=eligibility, test=None, **kwargs)
        self.syndromic_vds = syndromic_vds
        self.syndromic_uds = syndromic_uds
        return

    def notify_attendees(self, uids):
        ppl = self.sim.people
        f_uids = uids[ppl.female[uids]]
        m_uids = uids[ppl.male[uids]]
        if len(f_uids):
            self.syndromic_vds.step(uids=f_uids)
        if len(m_uids):
            self.syndromic_uds.step(uids=m_uids)
        return


class SyphilisANCTimer(ss.Intervention):
    """Schedule one ANC syph test event per pregnancy at a realistic week.

    In Zimbabwe many pregnant women do not attend ANC in tri1 as WHO
    recommends; visits are spread across weeks 8-32 of gestation. This
    intervention draws a single visit-week for each newly-conceived
    woman from Uniform(8, 32) and marks her as ANC-test-eligible on
    that timestep. Downstream `SyphTest` interventions read from
    ``today_uids`` to fire the actual test.

    States:
        ti_anc_visit (FloatArr): timestep on which the woman will
            attend her ANC visit. NaN if not pregnant / not scheduled.

    Properties:
        today_uids: UIDs whose ti_anc_visit == current ti and who are
            still alive + still pregnant.

    Pars:
        visit_week_low  (int): lower bound of visit-week draw. Default 8.
        visit_week_high (int): upper bound. Default 32.
    """

    def __init__(self, pars=None, name='syph_anc_timer', **kwargs):
        super().__init__(name=name)
        self.define_pars(
            visit_week=ss.uniform(low=8, high=32),  # CRN-safe Dist
        )
        self.update_pars(pars=pars, **kwargs)
        self.define_states(
            ss.FloatArr('ti_anc_visit', default=np.nan,
                        label='ti of scheduled ANC visit'),
        )
        return

    def _schedule(self, uids):
        """Draw a visit-week per woman and convert to a future ti."""
        if len(uids) == 0:
            return
        preg = self.sim.demographics.pregnancy
        # CRN-safe per-agent draw; ss.uniform().rvs keys on uids.
        weeks = self.pars.visit_week.rvs(uids)
        # Convert weeks → ti steps. preg.ti_pregnant[uids] is the
        # conception ti; visit_ti = conception_ti + round(weeks / weeks_per_step).
        # dt_year is the timestep duration in years; *52 → weeks per step.
        weeks_per_step = self.t.dt_year * 52.0 if self.t.dt_year else 4.33
        steps_to_visit = np.round(weeks / max(weeks_per_step, 1e-6)).astype(int)
        self.ti_anc_visit[uids] = preg.ti_pregnant[uids] + steps_to_visit

    def init_post(self):
        super().init_post()
        # Cover the cohort already pregnant at sim start so they don't
        # miss out. Treat them like newly-conceived for scheduling.
        if hasattr(self.sim.demographics, 'pregnancy'):
            preg = self.sim.demographics.pregnancy
            self._schedule(preg.pregnant.uids)

    def step(self):
        if not hasattr(self.sim.demographics, 'pregnancy'):
            return
        preg = self.sim.demographics.pregnancy
        new_preg = preg.pregnant.uids[preg.ti_pregnant[preg.pregnant.uids] == self.ti]
        self._schedule(new_preg)

    @property
    def today_uids(self):
        if not hasattr(self.sim.demographics, 'pregnancy'):
            return ss.uids()
        preg = self.sim.demographics.pregnancy
        candidates = self.ti_anc_visit.notnan.uids
        if len(candidates) == 0:
            return ss.uids()
        due = candidates[self.ti_anc_visit[candidates] == self.ti]
        if len(due) == 0:
            return ss.uids()
        # Still pregnant + still alive at this ti
        return due[preg.pregnant[due] & self.sim.people.alive[due]]


def make_syph_testing(stop=2040, symp_test_prob=None, rdt_year=2012):
    """
    Symptomatic + ANC syphilis testing pathways.

    Three channels feed into a single SyphTx:
      1. Symptomatic test (GUD): agents with chancre or rash visible.
      2. ANC RPR screen (1980–rdt_year): serology for pregnant women.
      3. ANC dual RDT screen (rdt_year–stop): treponemal rapid test.

    ANC coverage ramps from ~20% (1980s) through a 2008 dip to ~95%
    (EMTCT era). The product switches from RPR (non-treponemal, detects
    active infection) to dual RDT (treponemal, lifelong positivity).
    """
    if symp_test_prob is None:
        symp_test_prob = pd.read_csv('data/symp_test_prob_soc.csv')

    syph_dx_df = pd.read_csv(f'data/syph_dx.csv')
    gud_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'gud'], name='SyphDx_gud')
    rpr_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'rpr'], name='SyphDx_rpr')
    dual_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'dual'], name='SyphDx_dual')

    anc_years = [1980, 1990, 1999, 2008, 2012, 2018, 2040]
    # PROOF-OF-CONCEPT VALUES (exp 22 v3, 2026-06-06): lowered to match the
    # effective ~17% per-pregnancy rate that produced 55 sustainers in
    # exp 22 v1's broken-but-passing setup. Values NOT defensible as
    # realistic Zimbabwe ANC coverage (real rates 60-70% pre-EMTCT
    # creeping to 90% by 2040) — used here only to test whether the
    # existing 12-parameter prior contains a corner that brackets data.
    # If yes, iterate upward toward realistic values; if no, the
    # structural problem is bigger than ANC pressure.
    anc_probs = [0.05, 0.10, 0.15, 0.15, 0.20, 0.20, 0.20]

    def syph_dx_eligibility(sim):
        """Treat anyone newly diagnosed positive by any syph test this step."""
        tests = [sim.interventions.syph_symp_test,
                 sim.interventions.syph_anc_rpr,
                 sim.interventions.syph_anc_rdt]
        pos = tests[0].ti_positive == tests[0].ti
        for t in tests[1:]:
            pos = pos | (t.ti_positive == t.ti)
        return pos.uids

    syph_tx = sti.SyphTx(name='syph_tx', label='syph_tx', eligibility=syph_dx_eligibility)

    # --- Symptomatic channel (unchanged) ---
    def syph_symp_eligibility(sim):
        syph = sim.diseases.syph
        return syph.chancre_visible | syph.rash_visible

    # dt_scale=False: the CSV values are per-symptomatic-episode (visible
    # chancres last ~1 month, the symptomatic window matches a single dt
    # step). With dt_scale=True (stisim default) these would have been
    # divided by 12 → effectively no symptomatic treatment of primary syph,
    # which was a silent bug.
    syph_symp_test = sti.SyphTest(
        name='syph_symp_test', label='syph_symp_test',
        product=gud_dx,
        test_prob_data=symp_test_prob,
        eligibility=syph_symp_eligibility,
        dt_scale=False,
    )

    # --- ANC channels (era-gated) ---
    # SyphilisANCTimer schedules a single ANC-visit timestep per pregnancy
    # at a realistic gestational week. The SyphTest products read from its
    # today_uids and (with dt_scale=False) the listed anc_probs values are
    # the per-visit testing probability.
    syph_anc_timer = SyphilisANCTimer()

    def anc_eligibility(sim):
        sched = sim.interventions.get('syph_anc_timer')
        if sched is None:
            return ss.uids()
        return sched.today_uids

    syph_anc_rpr = sti.SyphTest(
        name='syph_anc_rpr', label='syph_anc_rpr',
        product=rpr_dx,
        years=anc_years,
        test_prob_data=anc_probs,
        eligibility=anc_eligibility,
        dt_scale=False,
    )
    syph_anc_rpr.stop = rdt_year

    syph_anc_rdt = sti.SyphTest(
        name='syph_anc_rdt', label='syph_anc_rdt',
        product=dual_dx,
        years=anc_years,
        test_prob_data=anc_probs,
        eligibility=anc_eligibility,
        dt_scale=False,
    )
    syph_anc_rdt.start = rdt_year

    return [syph_anc_timer, syph_symp_test, syph_anc_rpr, syph_anc_rdt, syph_tx]


def make_testing(ng, ct, tv, bv, poc=None, pn_pars=None, stop=2040):

    intv_year = 2027

    # Handle inputs
    synd_end = intv_year if poc else stop

    # Testing interventions
    def seeking_care_vds(sim):
        dis = sim.diseases
        female = sim.people.female
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & female
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & female
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & female
        return (ng_care | ct_care | tv_care).uids

    def seeking_care_uds(sim):
        dis = sim.diseases
        male = sim.people.male
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & male
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & male
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & male
        return (ng_care | ct_care | tv_care).uids

    ng_tx = sti.GonorrheaTreatment(name='ng_tx', label='ng_tx')
    ct_tx = sti.STITreatment(diseases='ct', name='ct_tx', label='ct_tx')
    metronidazole = sti.STITreatment(diseases=['tv', 'bv'], name='metronidazole', label='metronidazole')
    treatments = [ng_tx, ct_tx, metronidazole]
    outcome_treatment_map = dict(
        all3=treatments,
        ngct=[ng_tx, ct_tx],
        mtnz=[metronidazole],
        none=[],
    )

    # Syndromic management of VDS
    syndromic_vds = SyndromicMgmt(
        name='syndromic_vds',
        label='syndromic_vds',
        stop=synd_end,
        diseases=[ng, ct, tv, bv],
        eligibility=seeking_care_vds,
        treatments=treatments,
        outcome_treatment_map=outcome_treatment_map,
    )

    syndromic_uds = SyndromicMgmt(
        name='syndromic_uds',
        label='syndromic_uds',
        stop=stop,
        diseases=[ng, ct, tv],
        eligibility=seeking_care_uds,
        treatments=treatments,
        outcome_treatment_map=outcome_treatment_map,
    )

    # Index cases: women & men whose NG or CT treatment fired this step,
    # excluding those who were themselves notified one step prior (avoid recursion).
    def just_treated(sim):
        ng_treated = sim.interventions.ng_tx.ti_treated == sim.interventions.ng_tx.ti
        ct_treated = sim.interventions.ct_tx.ti_treated == sim.interventions.ct_tx.ti
        if 'pn' in sim.interventions:
            pn = sim.interventions.pn
            previous_index = pn.ti_notified == (pn.ti - 1)
            return ((ng_treated | ct_treated) & ~previous_index).uids
        return (ng_treated | ct_treated).uids

    def make_pn():
        return SyndromicPN(
            eligibility=just_treated,
            syndromic_vds=syndromic_vds,
            syndromic_uds=syndromic_uds,
            name='pn', label='pn',
            **(pn_pars or {}),
        )

    intvs = [syndromic_vds, syndromic_uds, ng_tx, ct_tx, metronidazole]

    if poc:
        disease_treatment_map = {'ng': ng_tx, 'ct': ct_tx, 'tv': metronidazole}
        panel = sti.SymptomaticTesting(
            name='panel', label='panel',
            start=intv_year,
            diseases=[ng, ct, tv],
            eligibility=seeking_care_vds,
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
            p_mtnz=0.8,  # Probability of metronidazole treatment for TV
            negative_treatments=[metronidazole],
        )
        intvs.append(panel)

    if pn_pars is not None:
        intvs.append(make_pn())

    return intvs
