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


class PartnerNotification(ss.Intervention):
    """ Give presumptive NG+CT treatment to partners of people being treated for NG or CT """

    def __init__(self, pars=None, eligibility=None, treat_current=None, treat_previous=None, name=None, label=None, **kwargs):
        super().__init__(eligibility=eligibility, name=name, label=label)
        self.define_pars(
            p_notify=dict(
                current=ss.bernoulli(p=0.5),  # Probability of notifying current partners
                previous=ss.bernoulli(p=0.05),  # Probability of notifying previous partners
            ),
            p_attends=dict(
                current=ss.bernoulli(p=0.5),  # Probability that current partners will attend
                previous=ss.bernoulli(p=0.01),  # Probability that previous partners will attend
            ),
        )
        self.update_pars(pars, **kwargs)

        # Store the current and prior network
        self.nws = None  # Initialized in init_pre
        self.start = 2027

        # Store the test/treatment intervention that notified partners will be eligible to receive
        self.tx = dict(
            current=treat_current,  # Treatment for current partners
            previous=treat_previous,  # Treatment for prior partners
        )

        self.define_states(
            ss.FloatArr('ti_notified')
        )

        self.contacts = sc.objdict(
            current=sc.objdict(mf=None, fm=None),  # Current partners notified
            previous=sc.objdict(mf=None, fm=None),  # Current partners notified
        )

        return

    def init_pre(self, sim):
        super().init_pre(sim)
        self.nws = dict(
            current=sim.networks.structuredsexual,  # Current sexual network
            previous=sim.networks.priorpartners,  # Prior sexual network
        )

    def identify_contacts(self, uids):
        # Return UIDs of people that have been identified as contacts and should be notified

        # Find contacts
        for nwtype, nw in self.nws.items():
            m_edge_inds = np.isin(nw.p1, uids).nonzero()[-1]
            f_edge_inds = np.isin(nw.p2, uids).nonzero()[-1]
            m_idx = nw.p1[m_edge_inds]
            f_partners = nw.p2[m_edge_inds]
            f_idx = nw.p2[f_edge_inds]
            m_partners = nw.p1[f_edge_inds]

            # Females notified and attending
            notified_f = self.pars.p_notify[nwtype].filter(f_partners)
            attending_f = self.pars.p_attends[nwtype].filter(notified_f)
            fp_edge_inds = np.isin(nw.p2, attending_f).nonzero()[-1]
            successful_m_idx = nw.p1[fp_edge_inds] & m_idx
            mf_pairs = list(zip(successful_m_idx, attending_f))

            # Males notified and attending
            notified_m = self.pars.p_notify[nwtype].filter(m_partners)
            attending_m = self.pars.p_attends[nwtype].filter(notified_m)
            mp_edge_inds = np.isin(nw.p1, attending_m).nonzero()[-1]
            successful_f_idx = nw.p2[mp_edge_inds] & f_idx
            fm_pairs = list(zip(successful_f_idx, attending_m))

            # Store contacts
            self.ti_notified[attending_m | attending_f] = self.ti
            self.contacts[nwtype].mf = mf_pairs
            self.contacts[nwtype].fm = fm_pairs

        return

    def step(self):
        sim = self.sim

        if self.t.now('year') >= self.start:
            index_cases = self.eligibility(sim)
            if len(index_cases) > 0:
                self.identify_contacts(index_cases)

                # In this scenario, we just treat all the contacts same as index case
                for pstatus in ['current', 'previous']:
                    for pairkey, clist in self.contacts[pstatus].items():
                        if len(clist) > 0:

                            intv = self.sim.interventions[self.tx[pstatus][pairkey[0]].name]
                            idx_txdict = intv.treated_by_uid  # Index case treatment
                            idx_uids = [c[0] for c in clist]
                            partner_txdict = {tx: ss.uids([clist[idx_uids.index(uid)][1] for uid in uids if uid in idx_uids]) for tx, uids in idx_txdict.items()}  # Sorry :(

                            # Set treatment eligibility
                            for oc, partner_uids in partner_txdict.items():
                                if len(partner_uids):
                                    txs = intv.outcome_treatment_map[oc]
                                    for tx in txs:
                                        tx.eligibility = tx.eligibility | partner_uids

        return


def make_testing(ng, ct, tv, bv, time_units=None, poc=None, pn_pars=None, stop=2040):

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
        bv_care = dis.bv.symptomatic & (dis.bv.ti_seeks_care == dis.bv.ti) & female
        return (ng_care | ct_care | tv_care | bv_care).uids

    def seeking_care_uds(sim):
        dis = sim.diseases
        male = sim.people.male
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & male
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & male
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & male
        return (ng_care | ct_care | tv_care).uids

    ng_tx = sti.GonorrheaTreatment(name='ng_tx', label='ng_tx', **time_units)
    ct_tx = sti.STITreatment(diseases='ct', name='ct_tx', label='ct_tx', **time_units)
    metronidazole = sti.STITreatment(diseases=['tv', 'bv'], name='metronidazole', label='metronidazole', **time_units)
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
        **time_units
        )

    syndromic_uds = SyndromicMgmt(
        name='syndromic_uds',
        label='syndromic_uds',
        stop=stop,
        diseases=[ng, ct, tv],
        eligibility=seeking_care_uds,
        treatments=treatments,
        outcome_treatment_map=outcome_treatment_map,
        **time_units
    )

    # Partner treatment eligibility
    def just_treated(sim):
        """ Return UIDs of people who have been treated for NG or CT """
        ng_treated = sim.interventions.gonorrheatreatment.ti_treated == sim.interventions.gonorrheatreatment.ti
        ct_treated = sim.interventions.ct_tx.ti_treated == sim.interventions.ct_tx.ti
        # Exclude people who were the original index case
        previous_index = sim.interventions.treat_partners.ti_notified == (sim.interventions.treat_partners.ti - 1)
        return ((ng_treated | ct_treated) & ~previous_index).uids

    # Optionally add partner treatment
    if not poc:
        if pn_pars is None:
            intvs = [syndromic_vds, syndromic_uds, ng_tx, ct_tx, metronidazole]

        else:
            partner_notification = PartnerNotification(
                **pn_pars,
                eligibility=just_treated,
                name='treat_partners',
                label='treat_partners',
                treat_current=dict(m=syndromic_uds, f=syndromic_vds),
                treat_previous=dict(m=syndromic_uds, f=syndromic_vds),
                **time_units
            )

            intvs = [syndromic_vds, syndromic_uds, ng_tx, ct_tx, metronidazole, partner_notification]

    if poc:
        disease_treatment_map = {'ng': ng_tx, 'ct': ct_tx, 'tv': metronidazole}
        p_mtnz = 0.8  # Probability of metronidazole treatment for TV

        panel = sti.SymptomaticTesting(
            name='panel',
            label='panel',
            start=intv_year,
            diseases=[ng, ct, tv],
            eligibility=seeking_care_vds,
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
            p_mtnz=p_mtnz,
            negative_treatments=[metronidazole],
            **time_units
        )
        if pn_pars is None:
            intvs = [syndromic_vds, syndromic_uds, panel, ng_tx, ct_tx, metronidazole]

        else:
            partner_notification = PartnerNotification(
                eligibility=just_treated,
                name='treat_partners',
                label='treat_partners',
                treat_current=dict(m=syndromic_uds, f=syndromic_vds),
                treat_previous=dict(m=syndromic_uds, f=syndromic_vds),
                **time_units
            )

            intvs = [syndromic_vds, syndromic_uds, panel, ng_tx, ct_tx, metronidazole, partner_notification]

    return intvs
