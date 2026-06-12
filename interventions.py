"""
Custom interventions for the discharge valuation
"""

import stisim as sti
import starsim as ss
import numpy as np
import pandas as pd
import sciris as sc
from collections import defaultdict


class GonorrheaTreatmentFixed(sti.GonorrheaTreatment):
    """Workaround for upstream stisim bug: ``GonorrheaTreatment`` declares
    a ``FloatArr('rel_treat', default=1)`` AMR-tracking state, but the
    default never reaches the underlying ``.raw`` array — every agent's
    rel_treat stays at NaN, so ``new_treat_eff = NaN * base_treat_eff =
    NaN``, the ``treat_eff`` bernoulli always rejects, and **no NG
    infection is ever successfully cleared**. Diagnosed via 0 NG
    differences across all 5 arms despite different treatment volumes;
    confirmed by per-agent rel_treat = NaN.

    This subclass treats NaN as the documented default (1.0) when
    computing per-agent treatment effectiveness. Upstream fix would
    initialise rel_treat for new agents.
    """
    def set_treat_eff(self, uids):
        rt = self.rel_treat[uids]
        rt = np.where(np.isnan(rt), 1.0, rt)
        new_treat_eff = rt * self.pars.base_treat_eff
        self.pars.treat_eff.set(new_treat_eff)
        return


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


class PartnerNotificationNoCycle(sti.PartnerNotification):
    """
    PartnerNotification base class with A→B→A cycle prevention.

    Tracks ``last_notifier[uid]`` = the agent who most recently notified
    this uid. When that agent becomes an index case, the (index, partner)
    edge to their last_notifier is dropped — A→B→A back-notification is
    blocked while chain propagation A→B→C still works.

    Cycle prevention happens inside ``_build_partner_edges`` (edges
    filtered per-pair before notification/attendance bernoullis fire).
    After the step's notifications resolve, ``last_notifier`` is updated
    for newly-notified agents using the (index, partner) pair table
    stashed during the build.

    Caveats:
      - Single-slot last_notifier: only the *most recent* notifier is
        remembered. If C notifies B after A did, last_notifier[B]=C and
        A→B→A is no longer blocked. In practice notifications happen
        across many timesteps so this is rarely the bottleneck.
      - Prior-partner channel (PriorPartners) is not cycle-filtered —
        we don't use it (p_notify_previous=0 in our arms).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.define_states(
            ss.FloatArr('last_notifier', default=-1.0,
                        label='UID of most recent notifier'),
        )
        self._pair_partners = None
        self._pair_indices = None

    def _build_partner_edges(self, nw, index_uids):
        in_p1 = np.isin(nw.p1, index_uids)
        in_p2 = np.isin(nw.p2, index_uids)
        partner_uids = np.concatenate([nw.p2[in_p1], nw.p1[in_p2]])
        edge_types = np.concatenate([nw.edges.edge_type[in_p1],
                                     nw.edges.edge_type[in_p2]])
        index_per_edge = np.concatenate([nw.p1[in_p1], nw.p2[in_p2]])

        # Drop edges where the partner is itself an index case
        keep = ~np.isin(partner_uids, index_uids)
        partner_uids = partner_uids[keep]
        edge_types = edge_types[keep]
        index_per_edge = index_per_edge[keep]

        # Cycle prevention: drop (index, partner) edges where the partner
        # was the index's most recent notifier (A→B→A guard).
        if len(partner_uids):
            ln_of_idx = np.asarray(self.last_notifier[ss.uids(index_per_edge)])
            keep_nocycle = ln_of_idx != partner_uids.astype(float)
            partner_uids = partner_uids[keep_nocycle]
            edge_types = edge_types[keep_nocycle]
            index_per_edge = index_per_edge[keep_nocycle]

        # Stash for last_notifier update at end of step
        self._pair_partners = partner_uids
        self._pair_indices = index_per_edge

        partner_edges = defaultdict(list)
        for uid, et in zip(partner_uids, edge_types):
            partner_edges[int(uid)].append(int(et))
        return partner_edges

    def init_results(self):
        super().init_results()
        # Wasted-attendance endpoint: attendees with no current STI to find.
        # BV is intentionally excluded — PN is meant to interrupt sexual
        # transmission, and BV is not sexually transmitted in this model.
        # So an attendee whose only "infection" is BV still counts as a
        # wasted PN trip for STI-interruption purposes.
        #
        # False-alarm-index endpoint: indices who triggered PN but had no
        # current STI at the moment of treatment (their treatment was
        # over-treatment for at least one STI and they had no other STI
        # being correctly treated). Computed from tx.outcomes — STITreatment
        # builds outcomes[disease].{successful, unsuccessful, unnecessary}
        # per step. An index UID is "false alarm" if it appears in
        # outcomes[d].unnecessary for SOME STI d in {ng, ct, tv, syph} but
        # does NOT appear in outcomes[d].(successful|unsuccessful) for ANY
        # STI in the same set. Only NG/CT/TV/syph count — BV doesn't
        # justify partner notification.
        self.define_results(
            ss.Result('new_attended_no_sti', dtype=int,
                      label='PN attendees with no current STI',
                      auto_plot=False),
            ss.Result('new_index_no_sti', dtype=int,
                      label='PN indices over-treated (no STI at treatment)',
                      auto_plot=False),
        )

    def step(self):
        super().step()
        # Update last_notifier for newly-notified agents (ti_notified set
        # by parent.step on all attendees this step). For each attendee,
        # pick any matching (index, partner=attendee) pair from this step.
        partners = self._pair_partners
        indices = self._pair_indices
        attending = (self.ti_notified == self.ti).uids

        # Wasted-attendance count: attendees with no current STI to find.
        if len(attending):
            ppl = self.sim.people
            any_sti = (ppl.ng.infected | ppl.ct.infected |
                       ppl.tv.infected | ppl.syph.infected)
            n_none = int((~any_sti[attending]).sum())
            self.results['new_attended_no_sti'][self.ti] += n_none

        # False-alarm-index count: indices whose triggering treatment
        # didn't correspond to a real STI infection. See init_results
        # docstring for definition. Read from tx.outcomes — populated
        # by STITreatment.step earlier this timestep.
        target_diseases = {'ng', 'ct', 'tv', 'syph'}
        had_sti = ss.uids()       # treated and had at least one STI
        treated_any = ss.uids()   # treated for at least one STI (any outcome)
        for tx_name in ('ng_tx', 'ct_tx', 'metronidazole', 'syph_tx'):
            tx = self.sim.interventions.get(tx_name)
            if tx is None:
                continue
            outcomes = getattr(tx, 'outcomes', None)
            if outcomes is None:
                continue
            for key, val in outcomes.items():
                if key not in target_diseases:
                    continue
                if not hasattr(val, 'get'):
                    continue
                succ = val.get('successful', ss.uids())
                unsucc = val.get('unsuccessful', ss.uids())
                unnec = val.get('unnecessary', ss.uids())
                had_sti = had_sti | succ | unsucc
                treated_any = treated_any | succ | unsucc | unnec
        false_alarm = treated_any.remove(had_sti)
        if len(false_alarm):
            self.results['new_index_no_sti'][self.ti] += len(false_alarm)

        if partners is not None and len(partners) and len(attending):
            sort_idx = np.argsort(partners, kind='stable')
            p_sorted = partners[sort_idx]
            i_sorted = indices[sort_idx]
            first = np.searchsorted(p_sorted, attending, side='left')
            in_range = first < len(p_sorted)
            if in_range.any():
                safe_first = np.clip(first, 0, len(p_sorted) - 1)
                match = (p_sorted[safe_first] == attending) & in_range
                if match.any():
                    atts = attending[match]
                    chosen = i_sorted[first[match]]
                    self.last_notifier[atts] = chosen.astype(float)
        self._pair_partners = None
        self._pair_indices = None
        return


class SyndromicPN(PartnerNotificationNoCycle):
    """
    Partner notification adapted for syndromic STI treatment.

    On attendance, routes partners by sex through the appropriate
    syndromic-management intervention; partners are treated per the
    syndromic algorithm on the next timestep.

    Inherits cycle prevention from PartnerNotificationNoCycle. Looks up
    syndromic_vds / syndromic_uds by name at step time (symmetric with
    POCPN's panel/syph_pn_test lookup).

    Args:
        eligibility: Index-case selector, e.g. just-treated agents.
        syndromic_vds_name: name of the women's syndromic-mgmt intervention.
        syndromic_uds_name: name of the men's syndromic-mgmt intervention.
    """
    def __init__(self, eligibility,
                 syndromic_vds_name='syndromic_vds',
                 syndromic_uds_name='syndromic_uds', **kwargs):
        super().__init__(eligibility=eligibility, test=None, **kwargs)
        self._syndromic_vds_name = syndromic_vds_name
        self._syndromic_uds_name = syndromic_uds_name
        return

    def notify_attendees(self, uids):
        ppl = self.sim.people
        f_uids = uids[ppl.female[uids]]
        m_uids = uids[ppl.male[uids]]
        vds = self.sim.interventions.get(self._syndromic_vds_name)
        uds = self.sim.interventions.get(self._syndromic_uds_name)
        if len(f_uids) and vds is not None:
            vds.step(uids=f_uids)
        if len(m_uids) and uds is not None:
            uds.step(uids=m_uids)
        return


class POCPanel(sti.STITest):
    """
    POC etiological panel for NG/CT/TV. Replaces both syndromic_vds and
    syndromic_uds in POC scenarios: a single high-sensitivity molecular
    test for each pathogen, with each positive enqueued onto its matched
    treatment. Tested separately for each disease (per-disease accuracy).

    Accepts ``uids=`` so :class:`POCPN` can route partner-notification
    attendees directly into the panel, bypassing the symptomatic-care
    eligibility filter.

    Args:
        treatments: list of STITreatment instances to enqueue onto.
        diseases: list of disease modules with ``treatable`` / ``susceptible``
            states and ``new_true_pos`` / ``new_false_pos`` results.
        disease_treatment_map: {disease_name: treatment_intervention}.
            Defaults to inferring from ``treatments[*].disease``.
        sens, spec: scalar etiological-test accuracy. POC molecular tests
            run ~0.95 for both NG and CT; TV slightly lower in practice but
            kept at 0.95 here.
    """
    def __init__(self, treatments, diseases, disease_treatment_map=None,
                 sens=0.95, spec=0.95,
                 years=None, start=None, stop=None, eligibility=None,
                 name=None, label=None, **kwargs):
        super().__init__(years=years, start=start, stop=stop,
                         eligibility=eligibility, name=name, label=label,
                         test_prob_data=1.0)
        self.define_pars(
            sens_dist=ss.bernoulli(p=sens),
            spec_dist=ss.bernoulli(p=1 - spec),
            dt_scale=False,
        )
        self.update_pars(**kwargs)
        # Store NAMES not refs. The sim copies disease/treatment instances
        # at init, so any ref stashed at construction points to an
        # unallocated stale object. Resolve through sim.diseases /
        # sim.interventions at step time.
        self.disease_names = [d.name for d in sc.tolist(diseases)]
        self.treatment_names = [t.name for t in sc.tolist(treatments)]
        if disease_treatment_map is None:
            disease_treatment_map = {t.disease: t.name for t in sc.tolist(treatments)}
        else:
            disease_treatment_map = {
                dname: (tx.name if hasattr(tx, 'name') else tx)
                for dname, tx in disease_treatment_map.items()
            }
        self.disease_treatment_map = disease_treatment_map
        self.define_states(
            ss.FloatArr('ti_referred'),
            ss.FloatArr('ti_dismissed'),
        )

    @property
    def treatments(self):
        return [self.sim.interventions[n] for n in self.treatment_names]

    @property
    def diseases(self):
        return [self.sim.diseases[n] for n in self.disease_names]

    def init_results(self):
        super().init_results()
        self.define_results(
            ss.Result('new_care_seekers', dtype=int, label='Care seekers',
                      auto_plot=False),
            ss.Result('new_referred', dtype=int, label='Referred for treatment',
                      auto_plot=False),
        )

    def step(self, uids=None):
        ti = self.ti

        if self.t.now('year') >= self.stop:
            for tx in self.treatments:
                tx.eligibility = ss.uids()
            return
        if self.t.now('year') < self.start:
            return

        if uids is None:
            uids = self.check_eligibility()
            self.ti_tested[uids] = ti
        if len(uids) == 0:
            return

        any_pos_mask = np.zeros(len(uids), dtype=bool)
        for disease in self.diseases:
            treatable = disease.treatable[uids]
            susceptible = disease.susceptible[uids]
            tp_uids = ss.uids()
            fp_uids = ss.uids()
            if treatable.any():
                tp_uids = self.pars.sens_dist.filter(uids[treatable])
            if susceptible.any():
                fp_uids = self.pars.spec_dist.filter(uids[susceptible])

            pos_uids = tp_uids | fp_uids
            tx_name = self.disease_treatment_map.get(disease.name)
            if tx_name is not None and len(pos_uids):
                tx = self.sim.interventions[tx_name]
                tx.eligibility = tx.eligibility | pos_uids
            if len(pos_uids):
                any_pos_mask = any_pos_mask | np.isin(uids, pos_uids)

            disease.results['new_true_pos'][ti] += len(tp_uids)
            disease.results['new_false_pos'][ti] += len(fp_uids)
            disease.results['new_true_neg'][ti] += int(susceptible.sum()) - len(fp_uids)
            disease.results['new_false_neg'][ti] += int(treatable.sum()) - len(tp_uids)

        referred = uids[any_pos_mask]
        self.ti_referred[referred] = ti
        self.ti_dismissed[uids.remove(referred)] = ti
        return

    def update_results(self):
        super().update_results()
        ti = self.ti
        self.results['new_care_seekers'][ti] += int((self.ti_tested == ti).sum())
        self.results['new_referred'][ti] += int((self.ti_referred == ti).sum())
        return


class POCPN(PartnerNotificationNoCycle):
    """
    Partner notification adapted for POC etiological testing.

    On attendance, routes partners through:
      1. The POC NG/CT/TV panel (etiological dx, replaces syndromic_vds/uds).
      2. The POC syph PN test (rpr, non-treponemal RDT; 0.90 sens across
         primary/secondary/latent/tertiary, 0.05 FP on cured).

    Looks up both routed interventions by name through ``self.sim`` at
    step time. Stashing refs at construction would bind to instances
    that the sim has since cloned (their state arrays would be stale /
    unallocated).

    Inherits cycle prevention from PartnerNotificationNoCycle.

    Args:
        eligibility: Index-case selector (same as SyndromicPN).
        panel_name: name of the :class:`POCPanel` to route NG/CT/TV
            testing through.
        syph_pn_test_name: name of the syph PN test (rpr product).
    """
    def __init__(self, eligibility, panel_name='panel',
                 syph_pn_test_name='syph_pn_test', **kwargs):
        super().__init__(eligibility=eligibility, test=None, **kwargs)
        self._panel_name = panel_name
        self._syph_pn_test_name = syph_pn_test_name

    def notify_attendees(self, uids):
        if not len(uids):
            return
        panel = self.sim.interventions.get(self._panel_name)
        if panel is not None:
            panel.step(uids=uids)
        syph_pn_test = self.sim.interventions.get(self._syph_pn_test_name)
        if syph_pn_test is not None:
            syph_pn_test.step(uids=uids)
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


ANC_PROBS_REALISTIC = [0.20, 0.30, 0.40, 0.35, 0.55, 0.70, 0.85]
ANC_PROBS_POC = [0.05, 0.10, 0.15, 0.15, 0.20, 0.20, 0.20]
ANC_YEARS = [1980, 1990, 1999, 2008, 2012, 2018, 2040]


def make_syph_testing(stop=2040, symp_test_prob=None, rdt_year=2012,
                      anc_probs=None, anc_years=None,
                      poc=False, intv_year=2027):
    """
    Symptomatic + ANC syphilis testing pathways.

    Three channels feed into a single SyphTx:
      1. Symptomatic test (GUD): agents with chancre or rash visible.
      2. ANC RPR screen (1980-rdt_year): serology for pregnant women.
      3. ANC dual RDT screen (rdt_year-stop): treponemal rapid test.

    Args:
        anc_probs: per-visit ANC testing probabilities at the calendar
                   years in ``anc_years``. Default = ANC_PROBS_REALISTIC
                   (peak 70% by 2018, 85% by 2040 — defensible Zimbabwe
                   coverage matching reported EMTCT scale-up). For
                   bifurcation analysis use ANC_PROBS_POC, the
                   non-defensible proof-of-concept ramp from exps 22-23.
    """
    if symp_test_prob is None:
        symp_test_prob = pd.read_csv('data/symp_test_prob_soc.csv')
    if anc_probs is None:
        anc_probs = ANC_PROBS_REALISTIC
    if anc_years is None:
        anc_years = ANC_YEARS

    syph_dx_df = pd.read_csv(f'data/syph_dx.csv')
    # Two-channel syndromic syph dx:
    #   - Ulcer channel (chancre_visible | gudp.symptomatic) uses
    #     syndromic_gud (universal 0.8): real-world syndromic
    #     management of GUD presents is presumptive treatment of any
    #     ulcer-presenter (true syph or HSV/chancroid), regardless of
    #     stage. The gudp.symptomatic pool gives the false-positive
    #     presumptive-treatment population AND the latent-syph
    #     incidental-treatment pathway (latents who happen to have a
    #     concurrent non-syph ulcer get treated for syph too).
    #   - Rash channel (rash_visible) uses syndromic_rash (0.1
    #     universal): secondary-syph rash presenters rarely make it
    #     to STI-clinic syph treatment under real-world syndromic
    #     flows. Modelled as a weak fallback.
    gud_dx  = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'syndromic_gud'],
                         name='SyphDx_gud')
    rash_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'syndromic_rash'],
                         name='SyphDx_rash')
    rpr_dx  = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'rpr'],  name='SyphDx_rpr')
    dual_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'dual'], name='SyphDx_dual')

    def syph_dx_eligibility(sim):
        """Treat anyone newly diagnosed positive by any treatment-triggering
        syph test this step.

        ANC pathway:
          * Pre-intv_year (or non-POC arms): `syph_anc_rdt` positives go
            straight to treatment. This matches calibration era practice
            (no confirmatory step) and matches arm A throughout.
          * POC arms after intv_year: `syph_anc_confirm` (rpr-product
            confirm of dual RDT positives) replaces `syph_anc_rdt` in the
            treatment-triggering list. The dual RDT becomes screen-only
            so previously-cured women whose treponemal antibodies still
            light up the dual RDT don't get re-treated.

        Robust to optional tests: missing tests are skipped.
        """
        intv = sim.interventions
        treat_tests = ['syph_symp_test', 'syph_symp_test_poc',
                       'syph_rash_test', 'syph_anc_rpr',
                       'syph_pn_test']
        confirm = intv.get('syph_anc_confirm')
        # Switch to confirm only once confirm has started (post intv_year);
        # before that, anc_rdt remains the ANC treatment trigger even in
        # POC arms — otherwise pre-2027 ANC syph treatment silently
        # disappears in POC sims, breaking the calibration baseline.
        if confirm is not None and sim.now >= confirm.start:
            treat_tests.append('syph_anc_confirm')
        else:
            treat_tests.append('syph_anc_rdt')
        tests = [intv.get(n) for n in treat_tests]
        tests = [t for t in tests if t is not None]
        if not tests:
            return ss.uids()
        pos = tests[0].ti_positive == tests[0].ti
        for t in tests[1:]:
            pos = pos | (t.ti_positive == t.ti)
        return pos.uids

    syph_tx = sti.SyphTx(name='syph_tx', label='syph_tx', eligibility=syph_dx_eligibility)

    # --- Ulcer channel: chancre + non-syph GUD presenters ---
    def syph_symp_eligibility(sim):
        syph = sim.diseases.syph
        gudp = sim.diseases.gudp
        return syph.chancre_visible | gudp.symptomatic

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

    # --- POC ulcer channel (intervention scenarios) ---
    # When poc=True:
    #   * syph_symp_test_poc replaces syph_symp_test after intv_year for
    #     symptomatic ulcer presenters, using the gud2 product (0.95
    #     primary / 0.95 secondary / 0.05 elsewhere) — a definitive
    #     etiological POC test for ulcer-presenting syph.
    #   * syph_pn_test handles PN attendees, who are mostly asymptomatic
    #     (notified because their index partner just got diagnosed) and
    #     often in primary stage themselves (recently infected by the
    #     index). It uses the rpr (non-treponemal) product, picked
    #     deliberately over dual because (1) dual has only 0.20 sens for
    #     primary syph — exactly the stage PN-attendees are most likely
    #     in — whereas rpr is 0.90 across primary/secondary/latent/
    #     tertiary; and (2) dual gives 0.95 false-positive on previously
    #     cured patients (treponemal antibodies persist after cure) which
    #     blew up unnecessary re-treatment under elevated PN, while rpr
    #     turns negative after cure (sus_not_naive = 0.05). No
    #     eligibility filter — fires only when called with explicit uids
    #     from POCPN.notify_attendees.
    syph_symp_test_poc = None
    syph_pn_test = None
    if poc:
        gud2_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'gud2'],
                              name='SyphDx_gud2')
        rpr_pn_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'rpr'],
                                name='SyphDx_rpr_pn')
        syph_symp_test.stop = intv_year
        syph_symp_test_poc = sti.SyphTest(
            name='syph_symp_test_poc', label='syph_symp_test_poc',
            product=gud2_dx,
            test_prob_data=symp_test_prob,
            eligibility=syph_symp_eligibility,
            dt_scale=False,
        )
        syph_symp_test_poc.start = intv_year

        def _never_eligible(_sim):
            return ss.uids()

        syph_pn_test = sti.SyphTest(
            name='syph_pn_test', label='syph_pn_test',
            product=rpr_pn_dx,
            test_prob_data=1.0,
            eligibility=_never_eligible,
            dt_scale=False,
        )
        syph_pn_test.start = intv_year

    # --- Rash channel: secondary syph rash presenters (weak) ---
    def syph_rash_eligibility(sim):
        return sim.diseases.syph.rash_visible

    syph_rash_test = sti.SyphTest(
        name='syph_rash_test', label='syph_rash_test',
        product=rash_dx,
        test_prob_data=symp_test_prob,
        eligibility=syph_rash_eligibility,
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

    # ANC confirmatory POC test (POC arms only). The dual RDT used for
    # ANC screening has 0.95 false-positive on previously-cured women
    # (treponemal memory). Without confirmation, every previously-treated
    # woman who returns for ANC gets re-treated. In POC arms we add a
    # non-treponemal RPR confirmation step: only women whose dual RDT
    # AND rpr both fire positive proceed to syph_tx. The 0.05 FP-on-cured
    # of rpr cuts the over-treatment loop. Eligibility = women whose
    # syph_anc_rdt set ti_positive this step.
    syph_anc_confirm = None
    if poc:
        def anc_confirm_eligibility(sim):
            rdt = sim.interventions.get('syph_anc_rdt')
            if rdt is None:
                return ss.uids()
            return (rdt.ti_positive == rdt.ti).uids

        # Reuse rpr_pn_dx if it was built above (poc=True branch); else
        # build a new rpr product reference.
        try:
            anc_confirm_dx = rpr_pn_dx
        except NameError:
            anc_confirm_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'rpr'],
                                        name='SyphDx_rpr_anc_confirm')
        syph_anc_confirm = sti.SyphTest(
            name='syph_anc_confirm', label='syph_anc_confirm',
            product=anc_confirm_dx,
            test_prob_data=1.0,
            eligibility=anc_confirm_eligibility,
            dt_scale=False,
        )
        syph_anc_confirm.start = intv_year

    # syph_tx is listed last so its eligibility callback picks up
    # ti_positive == ti from every treatment-triggering test that fired
    # this step. Order matters: syph_anc_confirm runs AFTER syph_anc_rdt
    # (its eligibility reads rdt.ti_positive == ti).
    intvs = [syph_anc_timer, syph_symp_test, syph_rash_test,
             syph_anc_rpr, syph_anc_rdt]
    if syph_symp_test_poc is not None:
        intvs.append(syph_symp_test_poc)
    if syph_pn_test is not None:
        intvs.append(syph_pn_test)
    if syph_anc_confirm is not None:
        intvs.append(syph_anc_confirm)
    intvs.append(syph_tx)
    return intvs


# Baseline PN rates: per-edge notification + per-(edge, partner-sex) attendance.
# Stable = marital; casual partnerships have lower notify + attend rates.
# Shared between make_testing's baseline_pn_eligibility callable and make_pn.
BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}


def baseline_pn_eligibility(sim):
    """Index-case selector for the PN intervention: any agent whose
    NG/CT/TV/syph treatment fired this step. Cycle prevention is handled
    inside PartnerNotificationNoCycle (excludes (index, partner) edges
    where partner == index's last_notifier), so no time-windowed filter
    is applied here.
    """
    intv = sim.interventions
    masks = []
    for name in ('ng_tx', 'ct_tx', 'metronidazole', 'syph_tx'):
        tx = intv.get(name)
        if tx is not None:
            masks.append(tx.ti_treated == tx.ti)
    if not masks:
        return ss.uids()
    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m
    return combined.uids


def make_pn(poc=None, pn_pars=None):
    """Build the shared partner-notification intervention.

    PN is shared across all diseases — index pool draws from
    NG/CT/TV/syph treatments collectively, and notify/attend rates are
    set once (no per-disease stratification). Routing of attendees is
    poc-aware:

      * Non-POC (arm A): :class:`SyndromicPN` routes attendees through
        syndromic_vds/uds, which apply the empiric NG/CT/TV/BV
        treatment algorithm. Syph attendees fall out of the syndromic
        pathway unless they happen to present with a chancre.
      * POC (arms B/C/...): :class:`POCPN` routes attendees through the
        POC etiological NG/CT/TV panel + `syph_pn_test` (rpr product),
        applied unconditionally on attending uids. So a notified
        attendee gets the full POC workup regardless of symptoms.

    Both classes inherit cycle prevention from
    :class:`PartnerNotificationNoCycle`.

    Args:
        poc: True for arms B/C/...; False for arm A.
        pn_pars: optional dict of overrides. Recognized keys:
            ``notify_rates`` (dict edge→prob), ``attendance_rates``
            (dict edge→{f, m}→prob). Remaining keys forwarded to the
            PN class.
    """
    overrides = (pn_pars or {}).copy()
    notify = overrides.pop('notify_rates', BASELINE_NOTIFY)
    attend = overrides.pop('attendance_rates', BASELINE_ATTEND)
    pn_pars_built = dict(
        p_notify_current=ss.bernoulli(p=sti.pn_rates(notify)),
        p_attends_current=ss.bernoulli(p=sti.pn_rates(attend)),
        p_notify_previous=ss.bernoulli(p=0),   # current channel only
        p_attends_previous=ss.bernoulli(p=0),
    )
    if poc:
        pn = POCPN(
            eligibility=baseline_pn_eligibility,
            panel_name='panel',
            syph_pn_test_name='syph_pn_test',
            name='pn', label='pn',
            pars=pn_pars_built,
            **overrides,
        )
    else:
        pn = SyndromicPN(
            eligibility=baseline_pn_eligibility,
            syndromic_vds_name='syndromic_vds',
            syndromic_uds_name='syndromic_uds',
            name='pn', label='pn',
            pars=pn_pars_built,
            **overrides,
        )
    return pn


class FSWOutreach(POCPanel):
    """Periodic POC NG/CT/TV testing of currently-active FSW.

    Models the proactive sex-worker outreach programs (DREAMS, Sista2Sista,
    SAPPHIRE clinics in Zimbabwe) that test FSW for STIs on a fixed cadence
    regardless of symptoms. Reuses POCPanel internals: per-step bernoulli
    over `structuredsexual.fsw.uids`, per-pathogen sens/spec, positives
    enqueued onto the same ng_tx / ct_tx / metronidazole treatments. Also
    drops positives into the PN index pool (via standard
    tx.ti_treated == ti semantics on the next treatment step).

    The asymptomatic FSW reservoir is the structural bottleneck PN cannot
    reach (a client picks up NG from a FSW, may be asymptomatic or
    delayed-symptomatic, and even if he later seeks care he typically
    cannot or will not name the FSW for PN). Direct outreach is the only
    realistic way to break that chain.

    Args:
        coverage_per_step (float): per-step probability an active FSW
            gets screened. 0.10 ≈ ~70% annual reach at monthly dt.
        start (year): outreach begins. Default 2027 (intv_year).
        stop (year): outreach ends. Default 2040.
        diseases, treatments, disease_treatment_map: as for POCPanel.
        sens, spec: POC test accuracy. Default 0.95/0.95.
    """
    def __init__(self, coverage_per_step=0.10, **kwargs):
        # FSW outreach uses its own eligibility filter (active FSW only).
        super().__init__(eligibility=self._fsw_eligibility, **kwargs)
        # Per-agent bernoulli — converted via update_pars so it's CRN-safe
        # and gets registered with the sim.
        self.define_pars(
            coverage=ss.bernoulli(p=coverage_per_step),
        )

    def _fsw_eligibility(self, sim):
        """Currently-active FSW only. Per-step bernoulli applied inside
        check_eligibility (test_prob_data=1.0 on the parent class)."""
        fsw = sim.networks.structuredsexual.fsw.uids
        if len(fsw) == 0:
            return ss.uids()
        return self.pars.coverage.filter(fsw)


def make_testing(ng, ct, tv, bv, poc=None, stop=2040, fsw_outreach=False,
                 fsw_coverage_per_step=0.10):

    intv_year = 2027

    # Don't shorten syndromic_vds.stop / syndromic_uds.stop in POC mode.
    # SyndromicMgmt.step resets every linked treatment's eligibility to
    # ss.uids() on every post-stop step — which would wipe whatever
    # POCPanel sets on ng_tx/ct_tx/metronidazole, leaving no NG/CT/TV
    # treatment in POC arms. Instead, gate the syndromic care-seekers'
    # eligibility callable to return empty after intv_year so the step
    # is a clean no-op.
    synd_end = stop

    # Symptomatic care-seekers, baseline (pre-POC) — used by both
    # syndromic_vds/uds and the POCPanel.
    def _raw_seeking_care_vds(sim):
        dis = sim.diseases
        female = sim.people.female
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & female
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & female
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & female
        return (ng_care | ct_care | tv_care).uids

    def _raw_seeking_care_uds(sim):
        dis = sim.diseases
        male = sim.people.male
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & male
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & male
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & male
        return (ng_care | ct_care | tv_care).uids

    if poc:
        def seeking_care_vds(sim):
            if sim.now >= intv_year:
                return ss.uids()
            return _raw_seeking_care_vds(sim)

        def seeking_care_uds(sim):
            if sim.now >= intv_year:
                return ss.uids()
            return _raw_seeking_care_uds(sim)

        def seeking_care_any(sim):
            return _raw_seeking_care_vds(sim) | _raw_seeking_care_uds(sim)
    else:
        seeking_care_vds = _raw_seeking_care_vds
        seeking_care_uds = _raw_seeking_care_uds

        def seeking_care_any(sim):
            return seeking_care_vds(sim) | seeking_care_uds(sim)

    ng_tx = GonorrheaTreatmentFixed(name='ng_tx', label='ng_tx')
    ct_tx = sti.STITreatment(diseases='ct', name='ct_tx', label='ct_tx')
    metronidazole = sti.STITreatment(diseases=['tv', 'bv'], name='metronidazole', label='metronidazole')
    treatments = [ng_tx, ct_tx, metronidazole]
    outcome_treatment_map = dict(
        all3=treatments,
        ngct=[ng_tx, ct_tx],
        mtnz=[metronidazole],
        none=[],
    )

    # Syndromic management of VDS and UDS. Both stop at intv_year in POC mode
    # — the POC scenario replaces syndromic care entirely with POCPanel.
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
        stop=synd_end,
        diseases=[ng, ct, tv],
        eligibility=seeking_care_uds,
        treatments=treatments,
        outcome_treatment_map=outcome_treatment_map,
    )

    intvs = [syndromic_vds, syndromic_uds, ng_tx, ct_tx, metronidazole]
    if poc:
        # POC etiological panel: single eligibility filter for both sexes,
        # high-sensitivity molecular test per pathogen, no presumptive
        # metronidazole. Replaces syndromic_vds and syndromic_uds after
        # intv_year.
        disease_treatment_map = {'ng': ng_tx, 'ct': ct_tx, 'tv': metronidazole}
        panel = POCPanel(
            name='panel', label='panel',
            start=intv_year,
            diseases=[ng, ct, tv],
            eligibility=seeking_care_any,
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
        )
        intvs.append(panel)

    if fsw_outreach:
        # Direct FSW outreach: per-step bernoulli over active FSW.
        # Tests each sampled FSW for NG/CT/TV (same POC panel internals)
        # and enqueues positives onto the same treatments. Requires
        # poc=True semantically — the treatments must exist as-is.
        if not poc:
            raise ValueError("fsw_outreach=True requires poc=True (uses "
                             "POC treatment routing).")
        disease_treatment_map = {'ng': ng_tx, 'ct': ct_tx, 'tv': metronidazole}
        fsw_intv = FSWOutreach(
            coverage_per_step=fsw_coverage_per_step,
            name='fsw_outreach', label='fsw_outreach',
            start=intv_year, stop=stop,
            diseases=[ng, ct, tv],
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
        )
        intvs.append(fsw_intv)

    # PN intervention is built separately by make_pn() and appended at
    # the top level (make_interventions). That keeps the asymmetry
    # explicit: make_testing builds NG/CT/TV testing + treatments,
    # make_syph_testing builds syph testing + treatment, and make_pn
    # builds the single PN intervention shared across all diseases.

    return intvs
