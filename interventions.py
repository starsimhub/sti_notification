"""
Custom interventions for the discharge valuation
"""

import stisim as sti
import starsim as ss
import numpy as np
import pandas as pd

from pn import PartnerNotification, pn_rates


class SyndromicPN(PartnerNotification):
    """
    Partner notification adapted for syndromic STI treatment.

    On attendance, routes partners by sex through the appropriate
    syndromic-management intervention; partners are treated per the
    syndromic algorithm on the next timestep.

    Cycle prevention and the new_attended_no_sti / new_index_no_sti
    diagnostic results are provided by the base
    :class:`sti.PartnerNotification`; this subclass only overrides
    ``notify_attendees`` to route attendees by sex.

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



class POCPN(PartnerNotification):
    """
    Partner notification for the POC arm, switching at ``intv_year``.

    The POC arm must be identical to the SOC arm before ``intv_year``:
    pre-switch, attendees are routed through syndromic management exactly
    as :class:`SyndromicPN` does (by sex, to syndromic_vds/uds). From
    ``intv_year`` attendees are routed through the POC NG/CT/TV panel
    regardless of symptoms, so partners are treated only for infections
    they themselves test positive for.

    Looks up routed interventions by name through ``self.sim`` at step time.
    Stashing refs at construction would bind to instances that the sim has
    since cloned (their state arrays would be stale / unallocated).

    Args:
        eligibility: Index-case selector (same as SyndromicPN).
        panel_name: name of the POC panel intervention (default ``'panel'``).
        syndromic_vds_name: women's syndromic-mgmt intervention (pre-switch).
        syndromic_uds_name: men's syndromic-mgmt intervention (pre-switch).
        intv_year: year the POC routing switches on. Default 2027.
    """
    def __init__(self, eligibility, panel_name='panel',
                 syndromic_vds_name='syndromic_vds',
                 syndromic_uds_name='syndromic_uds',
                 intv_year=2027, **kwargs):
        super().__init__(eligibility=eligibility, test=None, **kwargs)
        self._panel_name = panel_name
        self._syndromic_vds_name = syndromic_vds_name
        self._syndromic_uds_name = syndromic_uds_name
        self._intv_year = intv_year

    def notify_attendees(self, uids):
        if not len(uids):
            return
        if self.sim.now < self._intv_year:
            ppl = self.sim.people
            vds = self.sim.interventions.get(self._syndromic_vds_name)
            uds = self.sim.interventions.get(self._syndromic_uds_name)
            f_uids = uids[ppl.female[uids]]
            m_uids = uids[ppl.male[uids]]
            if len(f_uids) and vds is not None:
                vds.step(uids=f_uids)
            if len(m_uids) and uds is not None:
                uds.step(uids=m_uids)
            return
        panel = self.sim.interventions.get(self._panel_name)
        if panel is not None:
            panel.step(uids=uids)
        return


# Baseline PN rates: per-edge notification + per-(edge, partner-sex) attendance.
# Stable = marital; casual partnerships have lower notify + attend rates.
BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}

INDEX_TREATMENTS = ('ng_tx', 'ct_tx', 'metronidazole')


def baseline_pn_eligibility(sim):
    """Index-case selector for PN: any agent whose NG, CT or metronidazole
    treatment fired this step. Cycle prevention is handled inside
    :class:`pn.PartnerNotification`.
    """
    intv = sim.interventions
    masks = []
    for name in INDEX_TREATMENTS:
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

    The index pool draws from NG/CT/metronidazole treatments collectively;
    notify/attend rates are set once (no per-disease stratification).
    Routing of attendees is poc-aware:

      * SOC: :class:`SyndromicPN` routes attendees through syndromic_vds/uds.
      * POC: :class:`POCPN` routes attendees through the POC NG/CT/TV panel,
        applied unconditionally on attending uids.

    Args:
        poc: True for the POC arm; falsy for SOC.
        pn_pars: optional dict of overrides. Recognized keys:
            ``notify_rates`` (dict edge->prob), ``attendance_rates``
            (dict edge->{f, m}->prob). Remaining keys forwarded to the
            PN class.
    """
    overrides = (pn_pars or {}).copy()
    notify = overrides.pop('notify_rates', BASELINE_NOTIFY)
    attend = overrides.pop('attendance_rates', BASELINE_ATTEND)
    pn_pars_built = dict(
        p_notify_current=ss.bernoulli(p=pn_rates(notify)),
        p_attends_current=ss.bernoulli(p=pn_rates(attend)),
        p_notify_previous=ss.bernoulli(p=0),   # current channel only
        p_attends_previous=ss.bernoulli(p=0),
    )
    cls = POCPN if poc else SyndromicPN
    kw = dict(panel_name='panel') if poc else dict(
        syndromic_vds_name='syndromic_vds', syndromic_uds_name='syndromic_uds')
    return cls(eligibility=baseline_pn_eligibility, name='pn', label='pn',
               pars=pn_pars_built, **kw, **overrides)


class FSWOutreach(sti.SymptomaticTesting):
    """Periodic NG/CT/TV testing of currently-active FSW.

    Models the proactive sex-worker outreach programs (DREAMS, Sista2Sista,
    SAPPHIRE clinics in Zimbabwe) that test FSW for STIs on a fixed
    cadence regardless of symptoms. Reuses :class:`sti.SymptomaticTesting`
    internals: per-step bernoulli over ``structuredsexual.fsw.uids``,
    per-pathogen sens/spec, positives enqueued onto ng_tx / ct_tx /
    metronidazole. Positives also drop into the PN index pool (via the
    standard ``tx.ti_treated == ti`` semantics on the next treatment step).

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
        diseases, treatments, disease_treatment_map: forwarded to
            :class:`sti.SymptomaticTesting`.
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
        """Currently-active FSW only, with per-step bernoulli."""
        fsw = sim.networks.structuredsexual.fsw.uids
        if len(fsw) == 0:
            return ss.uids()
        return self.pars.coverage.filter(fsw)


SYNDROMIC_TX_MIX_CERV = dict(
    all3=[0.50, 0.10],
    ngct=[0.20, 0.80],
    mtnz=[0.15, 0.00],
    none=[0.15, 0.10],
)
SYNDROMIC_TX_MIX_NONCERV = dict(
    all3=[0.40, 0.10],
    ngct=[0.10, 0.80],
    mtnz=[0.25, 0.00],
    none=[0.25, 0.10],
)
# POC etiological-test accuracy used for the symptomatic-testing panel
# and for FSW outreach. sti.SymptomaticTesting expects
# {disease: [F, M]} dicts.
# Base case (exp 07 onward): 95% sensitivity, 98% specificity per pathogen,
# reflecting reported NAAT-based POC performance (co-author review, Nov 2026).
# Specificity is swept 95-99.5% in run_scenarios.py (SPEC_SWEEP).
POC_SENS = {'ng': [0.95, 0.95], 'ct': [0.95, 0.95], 'tv': [0.95, 0.95]}
POC_SPEC = {'ng': [0.98, 0.98], 'ct': [0.98, 0.98], 'tv': [0.98, 0.98]}


def accuracy_dict(value, diseases=('ng', 'ct', 'tv')):
    """Expand a scalar sens/spec into the {disease: [F, M]} form."""
    if value is None or isinstance(value, dict):
        return value
    return {d: [float(value), float(value)] for d in diseases}


def make_testing(poc=None, stop=2040, poc_sens=None, poc_spec=None,
                 fsw_outreach=False,
                 fsw_coverage_per_step=0.10):

    intv_year = 2027
    sens = accuracy_dict(poc_sens) or POC_SENS
    spec = accuracy_dict(poc_spec) or POC_SPEC

    # Don't shorten syndromic_vds.stop / syndromic_uds.stop in POC mode.
    # sti.SyndromicManagement.step resets every linked treatment's
    # eligibility to ss.uids() on every post-stop step — which would
    # wipe whatever the POC panel sets on ng_tx/ct_tx/metronidazole,
    # leaving no NG/CT/TV treatment in POC arms. Instead, gate the
    # syndromic care-seekers' eligibility callable to return empty after
    # intv_year so the step is a clean no-op.
    synd_end = stop

    # Symptomatic care-seekers, baseline (pre-POC) — used by both
    # syndromic_vds/uds and the POC panel.
    def _raw_seeking_care_vds(sim):
        dis = sim.diseases
        female = sim.people.female
        ng_care = dis.ng.symptomatic & (dis.ng.ti_seeks_care == dis.ng.ti) & female
        tv_care = dis.tv.symptomatic & (dis.tv.ti_seeks_care == dis.tv.ti) & female
        ct_care = dis.ct.symptomatic & (dis.ct.ti_seeks_care == dis.ct.ti) & female
        # Symptomatic BV also presents as vaginal discharge. This relies on
        # SimpleBV (which has its own symptomatic + ti_seeks_care states);
        # BV is female-only, so it enters VDS but not the UDS path.
        bv_care = dis.bv.symptomatic & (dis.bv.ti_seeks_care == dis.bv.ti) & female
        return (ng_care | ct_care | tv_care | bv_care).uids

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

    ng_tx = sti.GonorrheaTreatment(name='ng_tx', label='ng_tx')
    ct_tx = sti.STITreatment(diseases='ct', name='ct_tx', label='ct_tx')
    metronidazole = sti.STITreatment(diseases=['tv', 'bv'], name='metronidazole', label='metronidazole')
    treatments = [ng_tx, ct_tx, metronidazole]
    outcome_tx_map = dict(
        all3=treatments,
        ngct=[ng_tx, ct_tx],
        mtnz=[metronidazole],
        none=[],
    )

    # Syndromic management of VDS and UDS. Use upstream
    # sti.SyndromicManagement with our project-specific tx_mix values.
    syndromic_pars = dict(
        tx_mix_cerv=SYNDROMIC_TX_MIX_CERV,
        tx_mix_noncerv=SYNDROMIC_TX_MIX_NONCERV,
    )
    syndromic_vds = sti.SyndromicManagement(
        name='syndromic_vds',
        label='syndromic_vds',
        stop=synd_end,
        diseases=['ng', 'ct', 'tv', 'bv'],
        eligibility=seeking_care_vds,
        treatments=treatments,
        outcome_tx_map=outcome_tx_map,
        pars=syndromic_pars,
    )

    syndromic_uds = sti.SyndromicManagement(
        name='syndromic_uds',
        label='syndromic_uds',
        stop=synd_end,
        diseases=['ng', 'ct', 'tv'],
        eligibility=seeking_care_uds,
        treatments=treatments,
        outcome_tx_map=outcome_tx_map,
        pars=syndromic_pars,
    )

    # Detection/diagnosis modules must precede the treatment modules in the
    # returned list: Starsim runs interventions in list order, once per
    # step, so a treatment module only sees eligibility set *before* it
    # runs this same step. syndromic_vds/uds already precede ng_tx/ct_tx/
    # metronidazole below; panel and fsw_intv (if enabled) must too, or
    # their positives set this step aren't picked up by ng_tx/ct_tx/
    # metronidazole until the *next* step -- a one-timestep treatment lag
    # that doesn't exist under syndromic management, and is large enough to
    # materially shift NG's endemic equilibrium under POC.
    detection = [syndromic_vds, syndromic_uds]
    if poc:
        # POC etiological panel: single eligibility filter for both sexes,
        # high-sensitivity molecular test per pathogen, no presumptive
        # metronidazole. Replaces syndromic_vds and syndromic_uds after
        # intv_year. negative_treatments=[] disables the metro-for-VDS-
        # negatives routing (p_mtnz defaults to 0 anyway, but the empty
        # list also avoids the iteration over None in
        # SymptomaticTesting.step).
        disease_treatment_map = {'ng': ng_tx, 'ct': ct_tx, 'tv': metronidazole}
        panel = sti.SymptomaticTesting(
            name='panel', label='panel',
            start=intv_year,
            diseases=['ng', 'ct', 'tv'],
            eligibility=seeking_care_any,
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
            negative_treatments=[],
            pars=dict(sens=sens, spec=spec),
        )
        detection.append(panel)

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
            diseases=['ng', 'ct', 'tv'],
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
            negative_treatments=[],
            pars=dict(sens=sens, spec=spec),
        )
        detection.append(fsw_intv)

    # PN intervention is built separately by make_pn() and appended at
    # the top level (make_interventions). That keeps the asymmetry
    # explicit: make_testing builds NG/CT/TV testing + treatments and
    # make_pn builds the single PN intervention.

    return detection + treatments


class CondomCounseling(ss.Intervention):
    """Condom promotion + risk-reduction counselling for the newly treated.

    Called "bundled prevention" in earlier drafts; renamed after co-author
    review. Base-case effect (eff=0.30 over 6 months) is anchored to
    Project RESPECT (30% fewer incident STIs at 6 months; Kamb 1998) and the
    USPSTF meta-analysis (pooled OR 0.66; Henderson 2020).

    When an agent is treated for an STI, with probability ``coverage`` they are
    enrolled in a protection window of ``dur``: during it their re-acquisition
    susceptibility (``rel_sus``) for the protected diseases is multiplied by
    ``(1 - eff)``. Acquisition only; onward transmission is left untouched.

    The multiplier is applied multiplicatively each step, matching how the
    disease risk factors and coinfection connectors (hiv_sti, bv) compose on
    ``rel_sus``. Each disease's ``step_state`` resets ``rel_sus[:] = 1`` and
    connectors re-apply their cofactors before interventions run, so
    multiplying the currently-protected set here both composes with those
    cofactors and self-expires when an agent leaves the protected set — no
    reset bookkeeping needed beyond ``ti_protect_end``.

    Protected diseases: NG / CT / TV.
    """

    def __init__(self, coverage=0.5, eff=0.30, dur=ss.months(6),
                 diseases=('ng', 'ct', 'tv'),
                 trigger_tx=('ng_tx', 'ct_tx', 'metronidazole'),
                 start=2027, name='condom_counseling', *args, **kwargs):
        super().__init__(name=name)
        self.define_pars(
            coverage=ss.bernoulli(p=coverage),
            eff=eff,
            dur=dur,
        )
        self.update_pars(*args, **kwargs)
        self.diseases = list(diseases)
        self.trigger_tx = list(trigger_tx)
        self.start = start
        self._window_steps = None
        self.define_states(
            ss.FloatArr('ti_protect_end', default=np.nan),
        )
        return

    def init_pre(self, sim):
        super().init_pre(sim)
        dt_year = sim.t.dt_year if sim.t.dt_year else 1 / 12
        dur_years = self.pars.dur.years if hasattr(self.pars.dur, 'years') else float(self.pars.dur)
        self._window_steps = max(1, int(round(dur_years / dt_year)))
        return

    def _newly_treated(self):
        ti = self.ti
        uids = ss.uids()
        for name in self.trigger_tx:
            tx = self.sim.interventions.get(name)
            if tx is None or not hasattr(tx, 'ti_treated'):
                continue
            uids = uids | (tx.ti_treated == ti).uids
        return uids

    def step(self):
        sim = self.sim
        if sim.now < self.start:
            return
        ti = self.ti

        treated = self._newly_treated()
        if len(treated):
            enroll = self.pars.coverage.filter(treated)
            if len(enroll):
                self.ti_protect_end[enroll] = ti + self._window_steps

        protected = (self.ti_protect_end > ti).uids
        if not len(protected):
            return
        # Multiply, don't overwrite: step_state has reset rel_sus[:]=1 and
        # connectors have re-applied their cofactors this step, so this
        # composes with them and self-expires when agents leave `protected`.
        factor = 1.0 - float(self.pars.eff)
        for d in self.diseases:
            dis = sim.diseases.get(d)
            if dis is None:
                continue
            dis.rel_sus[protected] *= factor
        return

    def init_results(self):
        super().init_results()
        self.define_results(
            ss.Result('n_protected', dtype=int, label='Currently protected',
                      auto_plot=False),
            ss.Result('new_enrolled', dtype=int, label='Newly enrolled',
                      auto_plot=False),
        )
        return

    def record_events(self):
        super().record_events()
        ti = self.ti
        self.results['n_protected'][ti] = int((self.ti_protect_end > ti).sum())
        self.results['new_enrolled'][ti] = int((self.ti_protect_end == ti + self._window_steps).sum())
        return


class CareSeekScaler(ss.Intervention):
    """Defer the symptomatic care-seeking multiplier to intv_year.

    Without this, scaling `p_symp_care` at sim construction rewrites
    history back to 1985 and pre-2027 trajectories diverge across cells.

    On the first step at or after `start`, each listed disease's
    `pars.p_symp_care` is multiplied (sex-stratified, clipped to 1.0).

    BV is included by default (exp 07 onward): a demand-generation campaign
    raises care-seeking for vaginal discharge irrespective of its cause, so
    symptomatic BV presentations rise alongside NG/CT/TV ones. This matters
    for the PPV of the POC test among presenters. If SimpleBV's
    `p_symp_care` is a scalar rather than an [F, M] pair, the female
    multiplier is applied.

    Note: `p_symp_care` is read at infection time (`set_care_seeking`), so
    only infections acquired after `start` use the scaled probability.
    """

    def __init__(self, mult=1.0, start=2027,
                 diseases=('ng', 'ct', 'tv', 'bv'),
                 name='care_seek_scaler', *args, **kwargs):
        super().__init__(name=name)
        self.update_pars(*args, **kwargs)
        if hasattr(mult, '__len__'):
            self.mult_f = float(mult[0])
            self.mult_m = float(mult[1])
        else:
            self.mult_f = self.mult_m = float(mult)
        self.start = start
        self.diseases = list(diseases)
        self._fired = False
        return

    def step(self):
        if self._fired or self.sim.now < self.start:
            return
        for d_name in self.diseases:
            disease = self.sim.diseases.get(d_name)
            if disease is None or 'p_symp_care' not in disease.pars:
                continue
            curr = disease.pars.p_symp_care
            if isinstance(curr, ss.Dist):   # e.g. SimpleBV: ss.bernoulli(p=0.3)
                curr.set(p=min(1.0, float(curr.pars.p) * self.mult_f))
            elif hasattr(curr, '__len__'):
                disease.pars.p_symp_care = [min(1.0, float(curr[0]) * self.mult_f),
                                            min(1.0, float(curr[1]) * self.mult_m)]
            else:
                disease.pars.p_symp_care = min(1.0, float(curr) * self.mult_f)
        self._fired = True
        return


class PNIntensitySwitch(ss.Intervention):
    """Defer the PN intensity ladder to intv_year.

    PartnerNotification runs at the baseline notify/attend rates from sim
    start (matching the calibration). At `start` (intv_year), this
    intervention swaps the existing PN's notify/attend Bernoulli
    probability callables to the scenario level. Without this, cells with
    different PN intensities have different pre-2027 trajectories because
    PN has been acting on transmission since 1985.

    Args:
        notify_rates: same shape accepted by ``pn_rates`` (dict edge->prob
            or edge->{f,m}->prob).
        attendance_rates: same shape.
        start: simulation year at which the switch fires.
        pn_name: name of the PN intervention to mutate (default 'pn').
    """

    def __init__(self, notify_rates, attendance_rates, start=2027,
                 pn_name='pn', name='pn_intensity_switch', *args, **kwargs):
        super().__init__(name=name)
        self.update_pars(*args, **kwargs)
        self.notify_rates = notify_rates
        self.attendance_rates = attendance_rates
        self.start = start
        self.pn_name = pn_name
        self._fired = False
        return

    def _find_intv(self, name):
        intvs = self.sim.interventions
        if hasattr(intvs, 'get'):
            found = intvs.get(name)
            if found is not None:
                return found
        for cand in intvs:
            if getattr(cand, 'name', None) == name:
                return cand
        return None

    def step(self):
        if self._fired or self.sim.now < self.start:
            return
        pn = self._find_intv(self.pn_name)
        if pn is None or not hasattr(pn, 'pars'):
            return
        from pn import pn_rates as _pn_rates
        if hasattr(pn.pars, 'p_notify_current'):
            pn.pars.p_notify_current.set(p=_pn_rates(self.notify_rates))
        if hasattr(pn.pars, 'p_attends_current'):
            pn.pars.p_attends_current.set(p=_pn_rates(self.attendance_rates))
        self._fired = True
        return
