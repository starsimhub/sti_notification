"""Slide 11: POC + PN moderate + BP moderate + care-seeking layered by intensity.

Builds on Slide 10. Anchors PN and BP at moderate and layers three
care-seeking intensity levels on top.

  conda run -n starsim python plot_slide11.py
"""
from __future__ import annotations

import pandas as pd

from plot_slide6 import build_ts_grid_figure, KAVG, TS

ARMS = {
    'SOC':                                  'SOC',
    'POC + PN mod + BP mod':                'POC_c-baseline_p-moderate_b-moderate',
    'POC + PN mod + BP mod + CS low':       'POC_c-low_p-moderate_b-moderate',
    'POC + PN mod + BP mod + CS mod':       'POC_c-moderate_p-moderate_b-moderate',
    'POC + PN mod + BP mod + CS high':      'POC_c-high_p-moderate_b-moderate',
}
ARM_C = {
    'SOC':                                  '#555555',
    'POC + PN mod + BP mod':                '#fed9a6',
    'POC + PN mod + BP mod + CS low':       '#fdb863',
    'POC + PN mod + BP mod + CS mod':       '#e08214',
    'POC + PN mod + BP mod + CS high':      '#b35806',
}


def main():
    k = pd.read_csv(KAVG)
    ts = pd.read_parquet(TS)
    build_ts_grid_figure(
        k, ts, ARMS, ARM_C,
        suptitle=('Layering care-seeking onto POC + moderate PN + moderate '
                  'bundled prevention'),
        caption_note=('PN and BP held at moderate. '
                      'Endpoint bar order: S=SOC, P=POC+PN mod+BP mod, +L/M/H=+CS low/mod/high.'),
        out_name='fig_slide11.png',
    )


if __name__ == '__main__':
    main()
