"""Condoms/counselling-for-the-diagnosed intervention (exp 06, mechanism b).

When an agent is treated for an STI, with probability ``coverage`` they are
enrolled in a protection window of ``dur``: during it their re-acquisition
susceptibility (``rel_sus``) for the discharging STIs is multiplied by
``(1 - eff)``. This is the simplest test of the exp-04 finding that the
binding constraint is the *cured index being reinfected* by still-untreated
concurrent partners — condoms/counselling protect that index for a while.

First-cut scope (deliberately narrow, see exp 04 SUMMARY):
  * Acquisition only (``rel_sus``). Onward ``rel_trans`` is left to the
    disease's own load/stage dynamics — not clobbered.
  * Applied to ng/ct/tv only — these have no other ``rel_sus`` modifier, so
    the intervention fully owns it. (syph rel_sus is touched by the
    hiv_syph connector; excluded to avoid a fight.)

Managed cleanly: each step the previously-managed agents are reset to 1.0,
then the currently-protected set is re-applied — so expiry needs no
bookkeeping beyond ``ti_protect_end``.
"""
from __future__ import annotations

import numpy as np
import starsim as ss


class CondomCounseling(ss.Intervention):
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

        # 1. Enroll newly-treated agents with probability `coverage`.
        treated = self._newly_treated()
        if len(treated):
            enroll = self.pars.coverage.filter(treated)
            if len(enroll):
                self.ti_protect_end[enroll] = ti + self._window_steps

        # 2. Reset previously-managed agents, re-apply to currently protected.
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
