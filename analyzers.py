"""
Local analyzers for the Zimbabwe sti_notification calibration.

SyphTransmissionEvents
    Tracks syphilis transmission events (source, destination, source stage,
    network attribution) via a monkey-patch on ``syph.set_prognoses``.
    Aggregates online into per-source counts (for Lorenz / superspreader
    analysis) and a (src_cat, dst_cat, stage) matrix (for the transmission
    matrix). Memory-bounded: a few hundred KB per sim regardless of
    transmission volume.

    Categories: F_fsw, F_other, M_client, M_other. Source stage one of
    primary, secondary, early_latent, late_latent, unknown.

    The matrix is restricted to ``events_window`` (default 2010-2025) to
    focus on the calibration plateau; per-source counts span the full sim.
"""

from collections import defaultdict
import numpy as np
import sciris as sc
import starsim as ss


class SyphTransmissionEvents(ss.Analyzer):
    """Aggregate syph transmission counts for Lorenz + transmission matrix.

    Args:
        events_window: (year_start, year_end) for the transmission matrix
            aggregation. Per-source counts always cover the full sim.
        name: analyzer name (default 'syph_transmission_events')
    """

    def __init__(self, events_window=(2010, 2025), name='syph_transmission_events',
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.events_window = events_window
        self.src_count = defaultdict(int)
        self.matrix = defaultdict(int)
        self.by_year = defaultdict(lambda: defaultdict(int))
        return

    def init_post(self):
        super().init_post()
        sim = self.sim
        # The model may not have syph (e.g. discharging-only runs); be defensive
        if not hasattr(sim.diseases, 'syph'):
            return
        syph = sim.diseases.syph
        nw = sim.networks.structuredsexual
        ppl = sim.people
        original = syph.set_prognoses
        src_count = self.src_count
        matrix = self.matrix
        by_year = self.by_year
        events_lo, events_hi = self.events_window

        def categorize(uid):
            if ppl.female[uid]:
                return 'F_fsw' if nw.fsw[uid] else 'F_other'
            return 'M_client' if nw.client[uid] else 'M_other'

        def stage_of(uid):
            if syph.primary[uid]: return 'primary'
            if syph.secondary[uid]: return 'secondary'
            if syph.early[uid]: return 'early_latent'
            if syph.late[uid]: return 'late_latent'
            return 'unknown'

        def instrumented(uids, source_uids=None, ti=None):
            if source_uids is not None and len(source_uids) > 0:
                cti = ti if ti is not None else syph.ti
                try:
                    year = int(syph.t.timevec[cti].year)
                except Exception:
                    year = -1
                src_arr = np.atleast_1d(source_uids)
                dst_arr = np.atleast_1d(uids)
                in_window = events_lo <= year < events_hi
                for s, d in zip(src_arr, dst_arr):
                    src_count[int(s)] += 1
                    if in_window:
                        key = (categorize(s), categorize(d), stage_of(s))
                        matrix[key] += 1
                        by_year[year][key] += 1
            return original(uids, source_uids, ti)

        syph.set_prognoses = instrumented
        return

    def step(self):
        # All work happens in the monkey-patched set_prognoses.
        return

    def as_dict(self):
        """Serializable snapshot for outputs."""
        return {
            'src_count': dict(self.src_count),
            'matrix': {f'{k[0]}|{k[1]}|{k[2]}': v
                       for k, v in self.matrix.items()},
            'by_year': {str(y): {f'{k[0]}|{k[1]}|{k[2]}': v
                                  for k, v in d.items()}
                        for y, d in self.by_year.items()},
            'events_window': list(self.events_window),
        }


class CareTimingAnalyzer(ss.Analyzer):
    """Per-episode "treated within N months of acquisition" metric, for
    one or more windows simultaneously (3mo + 6mo, etc.).

    Stricter than ``tx_success / new_inf`` (which counts ALL successful
    treatments and ALL new infections in window — re-infections inflate
    both num and denom, and treatments of pre-window infections inflate
    only the numerator). This metric is per-episode:

      ``{d}_inf_treated_within_{N}mo`` = "agent was newly infected at
      time T then successfully treated within N months of T".

    For each disease tracks a per-agent ``ti_last_inf`` (overwritten on
    every new infection event for that agent), then on each step
    inspects every linked treatment's ``outcomes[disease].successful``
    uids; for each successful uid checks whether
    ``(ti - ti_last_inf) <= window_steps_N`` for each window N. If yes,
    increments the corresponding result. A cure at 4 months counts for
    the 6mo result but not the 3mo result.

    Args:
        disease_names: list of disease names to track.
        treatment_disease_map: dict mapping treatment intervention name
            to disease name.
        windows_months: list of cure-timing windows in months
            (default [3, 6]).
        name: analyzer name (default 'care_timing').

    Reads:
        sim.diseases[d].ti_infected per step.
        sim.interventions[tx].outcomes[d].successful per step.

    Writes (per disease, per window):
        results[f'{d}_inf_treated_within_{N}mo'], indexed by the
        timestep on which the CURE happened. Sum over window for the
        numerator; pair with sim.results[d].new_infections for the
        denominator.

    Backwards-compat: accepts ``window_months=`` (singular) as well;
    converted to a one-element list internally.
    """
    def __init__(self, disease_names, treatment_disease_map,
                 windows_months=None, window_months=None,
                 name='care_timing', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.disease_names = list(disease_names)
        self.treatment_disease_map = dict(treatment_disease_map)
        if windows_months is None and window_months is not None:
            windows_months = [int(window_months)]
        if windows_months is None:
            windows_months = [3, 6]
        self.windows_months = [int(w) for w in windows_months]
        states = [ss.FloatArr(f'{d}_ti_last_inf', default=np.nan)
                  for d in self.disease_names]
        self.define_states(*states)

    def init_results(self):
        super().init_results()
        results = sc.autolist()
        for d in self.disease_names:
            for w in self.windows_months:
                results += [
                    ss.Result(f'{d}_inf_treated_within_{w}mo', dtype=int,
                              label=(f'{d} infections treated within '
                                     f'{w}mo of acquisition'),
                              auto_plot=False),
                ]
        self.define_results(*results)

    def step(self):
        sim = self.sim
        ti = self.ti
        dt_year = sim.t.dt_year if sim.t.dt_year else 1/12
        window_steps = {w: max(1, int(round(w / 12.0 / dt_year)))
                        for w in self.windows_months}

        # 1. Update ti_last_inf for agents newly infected this step.
        for d in self.disease_names:
            disease = sim.diseases.get(d)
            if disease is None:
                continue
            ti_arr = getattr(self, f'{d}_ti_last_inf')
            new_inf = (disease.ti_infected == ti).uids
            if len(new_inf):
                ti_arr[new_inf] = ti

        # 2. For each tracked treatment, check window membership.
        for tx_name, d in self.treatment_disease_map.items():
            tx = sim.interventions.get(tx_name)
            if tx is None:
                continue
            outcomes = getattr(tx, 'outcomes', None)
            if outcomes is None:
                continue
            disease_out = outcomes.get(d) if hasattr(outcomes, 'get') else None
            if disease_out is None:
                continue
            succ = disease_out.get('successful') if hasattr(disease_out, 'get') \
                   else getattr(disease_out, 'successful', None)
            if succ is None or len(succ) == 0:
                continue
            ti_arr = getattr(self, f'{d}_ti_last_inf')
            last_inf = ti_arr[succ]
            valid = ~np.isnan(last_inf)
            gap = ti - last_inf
            for w, n_steps in window_steps.items():
                in_window = valid & (gap <= n_steps)
                n_in = int(in_window.sum())
                if n_in:
                    self.results[f'{d}_inf_treated_within_{w}mo'][ti] += n_in
        return
