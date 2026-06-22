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
    Partner notification adapted for POC etiological testing.

    On attendance, routes partners through:
      1. The POC NG/CT/TV panel (etiological dx, replaces syndromic_vds/uds).
      2. The POC syph PN test (rpr, non-treponemal RDT; 0.90 sens across
         primary/secondary/latent/tertiary, 0.05 FP on cured).

    Looks up both routed interventions by name through ``self.sim`` at
    step time. Stashing refs at construction would bind to instances
    that the sim has since cloned (their state arrays would be stale /
    unallocated).

    Cycle prevention + diagnostic results come from the base
    :class:`sti.PartnerNotification`.

    Args:
        eligibility: Index-case selector (same as SyndromicPN).
        panel_name: name of the symptomatic-testing panel intervention to
            route NG/CT/TV testing through (defaults to ``'panel'``).
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
    # rel_test scales the per-step test probability inside SyphTest
    # (stisim base STITest line ~195: test_prob *= self.pars.rel_test,
    # then clipped to [0, 1]). For care-seeking demand-gen we apply
    # care_seek_mult as a MULTIPLIER on top of whatever rel_test ends
    # up at — which matters because the calibration pipeline overrides
    # syph_symp_test.rel_test via set_pars_local after construction.
    # The applied scaling happens in build_sim (run.py) post-init, NOT
    # here at construction time. ANC pathway is not scaled — ANC is
    # opportunistic, not care-seeking-driven.
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
    inside the upstream :class:`sti.PartnerNotification` (drops
    ``(index, partner)`` edges where ``last_notifier[index] == partner``),
    so no time-windowed filter is applied here.
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

    Cycle prevention and the new_attended_no_sti / new_index_no_sti
    diagnostic results are provided by the upstream
    :class:`sti.PartnerNotification`; we just pass ``diseases`` and
    ``index_treatments`` so the upstream class can compute them.

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
        p_notify_current=ss.bernoulli(p=pn_rates(notify)),
        p_attends_current=ss.bernoulli(p=pn_rates(attend)),
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
POC_SENS = {'ng': [0.95, 0.95], 'ct': [0.95, 0.95], 'tv': [0.95, 0.95]}
POC_SPEC = {'ng': [0.95, 0.95], 'ct': [0.95, 0.95], 'tv': [0.95, 0.95]}


def make_testing(poc=None, stop=2040, fsw_outreach=False,
                 fsw_coverage_per_step=0.10):

    intv_year = 2027

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

    intvs = [syndromic_vds, syndromic_uds, ng_tx, ct_tx, metronidazole]
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
            pars=dict(sens=POC_SENS, spec=POC_SPEC),
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
            diseases=['ng', 'ct', 'tv'],
            treatments=treatments,
            disease_treatment_map=disease_treatment_map,
            negative_treatments=[],
            pars=dict(sens=POC_SENS, spec=POC_SPEC),
        )
        intvs.append(fsw_intv)

    # PN intervention is built separately by make_pn() and appended at
    # the top level (make_interventions). That keeps the asymmetry
    # explicit: make_testing builds NG/CT/TV testing + treatments,
    # make_syph_testing builds syph testing + treatment, and make_pn
    # builds the single PN intervention shared across all diseases.

    return intvs


class CondomCounseling(ss.Intervention):
    """Condoms/counselling for the diagnosed (promoted from archived exp 06).

    When an agent is treated for an STI, with probability ``coverage`` they are
    enrolled in a protection window of ``dur``: during it their re-acquisition
    susceptibility (``rel_sus``) for the discharging STIs is multiplied by
    ``(1 - eff)``. Acquisition only (ng/ct/tv); onward transmission and syph
    rel_sus are left untouched. Each step previously-managed agents are reset to
    1.0 and the currently-protected set re-applied, so expiry needs no extra
    bookkeeping beyond ``ti_protect_end``.
    """

    def __init__(self, coverage=0.5, eff=0.5, dur=ss.months(6),
                 diseases=('ng', 'ct', 'tv'),
                 trigger_tx=('ng_tx', 'ct_tx', 'metronidazole', 'syph_tx'),
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
        self._managed = ss.uids()
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
        factor = 1.0 - float(self.pars.eff)
        for d in self.diseases:
            dis = sim.diseases.get(d)
            if dis is None:
                continue
            if len(self._managed):
                dis.rel_sus[self._managed] = 1.0
            if len(protected):
                dis.rel_sus[protected] = factor
        self._managed = protected
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

    def update_results(self):
        super().update_results()
        ti = self.ti
        self.results['n_protected'][ti] = len(self._managed)
        self.results['new_enrolled'][ti] = int((self.ti_protect_end == ti + self._window_steps).sum())
        return
