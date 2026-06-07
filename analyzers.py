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
