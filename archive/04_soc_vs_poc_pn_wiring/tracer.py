"""Instrumentation for the STI partner-notification chain trace (exp 04).

STIChainTracer is an analyzer that captures the two things the chain
reconstruction needs that aren't otherwise persisted per-step, for a
chosen discharging STI (``disease`` / ``tx_name``):

  1. ``tx_events`` — per-step treatment outcomes. ``<tx>.outcomes`` is
     recomputed and overwritten every step, so we snapshot the
     successful / unsuccessful UIDs each step inside the window.
  2. ``trans_events`` — per-event transmission (source → target),
     captured by monkey-patching ``<disease>.set_prognoses`` (same
     technique as analyzers.SyphTransmissionEvents). This is what lets a
     reinfection be attributed to a specific source agent.

Combined with the dyad-level ``pn.trace_events`` log (index → partner →
notified → attended), these reconstruct named A→B(→C) chains.

Default disease is CT: in the rc1.5.7 calibration only syph + HIV + FSW
prevalence were targets, so the discharging-STI betas are free priors and
some draws (e.g. 773) drive NG/TV extinct. CT sustains and its treatment
cures (~89%), so it's the discharging STI where PN chains are observable.

Window-bounded so memory stays small and the cohort + its reinfections
sit well inside the sim.
"""
from __future__ import annotations

import numpy as np
import starsim as ss


class STIChainTracer(ss.Analyzer):
    def __init__(self, disease='ct', tx_name='ct_tx', window=(2030, 2034),
                 name='sti_chain_tracer', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.disease = disease
        self.tx_name = tx_name
        self.window = window
        self.tx_events = []     # (ti, uid, 'success'|'fail')
        self.trans_events = []  # (ti, source_uid, target_uid, src_cat)
        return

    def _year(self, ti):
        try:
            return int(self.sim.t.timevec[ti].year)
        except Exception:
            return -1

    def init_post(self):
        super().init_post()
        dis = self.sim.diseases.get(self.disease)
        if dis is None:
            return
        original = dis.set_prognoses
        trans = self.trans_events
        lo, hi = self.window
        nw = self.sim.networks.get('structuredsexual')
        ppl = self.sim.people

        def categorize(uid):
            # Captured at transmission time — FSW/client status is dynamic.
            if ppl.female[uid]:
                return 'fsw' if (nw is not None and nw.fsw[uid]) else 'f_other'
            return 'client' if (nw is not None and nw.client[uid]) else 'm_other'

        def instrumented(uids, sources=None):
            ti = dis.ti
            try:
                year = int(dis.t.timevec[ti].year)
            except Exception:
                year = -1
            if sources is not None and lo <= year < hi:
                src = np.atleast_1d(sources)
                dst = np.atleast_1d(uids)
                for s, d in zip(src, dst):
                    sf = float(s)
                    if np.isfinite(sf):
                        si = int(sf)
                        trans.append((int(ti), si, int(d), categorize(si)))
            return original(uids, sources)

        dis.set_prognoses = instrumented
        return

    def step(self):
        sim = self.sim
        ti = self.ti
        lo, hi = self.window
        if not (lo <= self._year(ti) < hi):
            return
        tx = sim.interventions.get(self.tx_name)
        outcomes = getattr(tx, 'outcomes', None) if tx is not None else None
        if outcomes is None:
            return
        out = outcomes.get(self.disease) if hasattr(outcomes, 'get') else None
        if out is None:
            return
        for key, tag in (('successful', 'success'), ('unsuccessful', 'fail')):
            uids = out.get(key) if hasattr(out, 'get') else None
            if uids is None:
                continue
            for u in uids:
                self.tx_events.append((int(ti), int(u), tag))
        return
