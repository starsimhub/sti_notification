"""Slide 9: POC + partner notification layered by intensity.

Builds on Slide 6 (SOC vs POC-alone) by adding three PN intensity levels
(low / moderate / high) on top of the POC arm. Care-seeking and bundled
prevention are held at baseline.

Story: at moderate PN we start to see meaningful prevalence declines; at
high PN they're clearer still. Incidence remains high because reinfection
from the residual reservoir persists.

  conda run -n starsim python plot_slide9.py
"""
from __future__ import annotations

import pandas as pd

from plot_slide6 import build_ts_grid_figure, KAVG, TS

ARMS = {
    'SOC':           'SOC',
    'POC alone':     'POC_c-baseline_p-baseline_b-none',
    'POC + PN low':  'POC_c-baseline_p-low_b-none',
    'POC + PN mod':  'POC_c-baseline_p-moderate_b-none',
    'POC + PN high': 'POC_c-baseline_p-high_b-none',
}
ARM_C = {
    'SOC':           '#555555',
    'POC alone':     '#fed9a6',
    'POC + PN low':  '#fdb863',
    'POC + PN mod':  '#e08214',
    'POC + PN high': '#b35806',
}


def main():
    k = pd.read_csv(KAVG)
    ts = pd.read_parquet(TS)
    build_ts_grid_figure(k, ts, ARMS, ARM_C, out_name='fig_slide9.png')


if __name__ == '__main__':
    main()
