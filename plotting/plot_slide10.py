"""Slide 10: POC + PN moderate + bundled prevention layered by intensity.

Builds on Slide 9. Anchors PN at moderate (from the previous slide's
best-of-three) and layers three bundled-prevention intensity levels on top.

  conda run -n starsim python plot_slide10.py
"""
from __future__ import annotations

import pandas as pd

from plot_slide6 import build_ts_grid_figure, KAVG, TS

ARMS = {
    'SOC':                       'SOC',
    'POC + PN mod':              'POC_c-baseline_p-moderate_b-none',
    'POC + PN mod + BP low':     'POC_c-baseline_p-moderate_b-low',
    'POC + PN mod + BP mod':     'POC_c-baseline_p-moderate_b-moderate',
    'POC + PN mod + BP high':    'POC_c-baseline_p-moderate_b-high',
}
ARM_C = {
    'SOC':                       '#555555',
    'POC + PN mod':              '#fed9a6',
    'POC + PN mod + BP low':     '#fdb863',
    'POC + PN mod + BP mod':     '#e08214',
    'POC + PN mod + BP high':    '#b35806',
}


def main():
    k = pd.read_csv(KAVG)
    ts = pd.read_parquet(TS)
    build_ts_grid_figure(
        k, ts, ARMS, ARM_C,
        suptitle=('Layering bundled prevention onto POC + moderate '
                  'partner notification'),
        caption_note=('PN held at moderate; care-seeking at baseline. '
                      'Endpoint bar order: S=SOC, P=POC+PN mod, +L/M/H=+BP low/mod/high.'),
        out_name='fig_slide10.png',
    )


if __name__ == '__main__':
    main()
