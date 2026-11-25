"""Compute the diagnostic-performance table (sens/spec/PPV/NPV/FDR/FOR)
for Slide 4.

Sens/spec inputs come from three places:

* NG / CT under SOC syndromic management: the female tx_mix in
  ``interventions.py``. The cerv table (used when the woman IS
  symptomatic for NG or CT) gives ``all3=0.50``, ``ngct=0.20``, so
  ``P(treated for NG/CT | has NG/CT) = 0.70`` → sens = 0.70. The
  noncerv table (used when she is NOT symptomatic for NG/CT) gives
  ``all3=0.40``, ``ngct=0.10``, so ``P(treated for NG/CT | no NG/CT) =
  0.50`` → 1 - spec = 0.50, spec = 0.50.
* TV under SOC syndromic management: metronidazole fires on
  ``all3 + mtnz`` in either mix (cerv: 0.50+0.15=0.65; noncerv:
  0.40+0.25=0.65), and metro-routing doesn't depend on TV status
  itself, so sens_TV = spec_TV rate = 0.65 (i.e. sens = 0.65,
  spec = 0.35).
* POC panel (NG / CT / TV): the female values of ``interventions.py::POC_SENS``
  and ``POC_SPEC`` (base case 95% sensitivity, 98% specificity).

Prevalences among VDS presenters come from ``results/vds_etiology.csv``.

    conda run -n starsim python plotting/compute_slide4_ppv.py
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from interventions import POC_SENS, POC_SPEC  # noqa: E402
VDS_CSV = REPO / 'results' / 'vds_etiology.csv'
OUT = REPO / 'results' / 'slide4_diagnostic_performance.csv'

DISEASES = [('ng', 'Gonorrhoea'),
            ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis')]

SENS = {
    ('SOC', 'ng'):   0.70,   # tx_mix_cerv: all3 (0.50) + ngct (0.20)
    ('SOC', 'ct'):   0.70,   # NG/CT are co-routed
    ('SOC', 'tv'):   0.65,   # tx_mix: all3 + mtnz in either mix
    **{('POC', d): POC_SENS[d][0] for d, _ in DISEASES},  # female value
}
SPEC = {
    ('SOC', 'ng'):   0.50,   # tx_mix_noncerv: 1 - (all3 0.40 + ngct 0.10)
    ('SOC', 'ct'):   0.50,
    ('SOC', 'tv'):   0.35,   # 1 - 0.65 metro rate
    **{('POC', d): POC_SPEC[d][0] for d, _ in DISEASES},  # female value
}


def main():
    vd = dict(zip(*[pd.read_csv(VDS_CSV)[c] for c in ('metric', 'value')]))
    prev = {'ng':   vd['marg_ng'],
            'ct':   vd['marg_ct'],
            'tv':   vd['marg_tv']}

    rows = []
    for dkey, dname in DISEASES:
        p = prev[dkey]
        for arm in ('SOC', 'POC'):
            sens = SENS[(arm, dkey)]
            spec = SPEC[(arm, dkey)]
            tp = sens * p
            fp = (1 - spec) * (1 - p)
            fn = (1 - sens) * p
            tn = spec * (1 - p)
            ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
            fdr = 1 - ppv
            for_rate = 1 - npv  # false-omission rate
            rows.append({
                'disease':    dname,
                'arm':        arm,
                'prev':       p,
                'sens':       sens,
                'spec':       spec,
                'PPV':        ppv,
                'NPV':        npv,
                'FDR':        fdr,
                'FOR':        for_rate,
            })
    df = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, float_format='%.3f')
    print(f'wrote {OUT}\n')
    # Print as percentages for the slide
    disp = df.copy()
    for col in ('prev', 'sens', 'spec', 'PPV', 'NPV', 'FDR', 'FOR'):
        disp[col] = (100 * disp[col]).round(0).astype(int)
    print(disp.to_string(index=False))


if __name__ == '__main__':
    main()
