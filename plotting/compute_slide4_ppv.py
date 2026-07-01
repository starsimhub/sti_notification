"""Compute the diagnostic-performance table (sens/spec/PPV/NPV/FDR/FOR)
for Slide 4.

Sens/spec inputs come from three places:

* NG / CT under SOC syndromic management: the female tx_mix in
  ``scenarios.py`` — ``all3=0.40``, ``ngct=0.10``, ``mtnz=0.25``,
  ``none=0.25`` (both cerv and noncerv strata use the same mix in this
  project). NG treatment fires on ``all3 + ngct = 0.50`` regardless of
  infection status, so sens = 1 - spec = 0.50 for both NG and CT.
* TV under SOC syndromic management: metronidazole fires on
  ``all3 + mtnz = 0.65`` → sens = 0.65, spec = 0.35.
* POC panel (NG / CT / TV): ``interventions.py::POC_SENS = POC_SPEC = 0.95``.

Syphilis follows a different pathway (RPR or dual RDT at ANC + PN, not
VDS). Headline values:

* SOC (dual RDT): sens ≈ 0.70 (weighted across active-disease stages:
  0.20 primary + 0.95 secondary/latent). Spec ≈ 0.85 (dual is 0.99
  specific on naive women but 0.05 on previously-cured; weighted with
  ~15 % cured share this gives ~0.85).
* POC (RPR): sens = 0.90, spec = 0.95 (``data/syph_dx.csv``, ``rpr``
  rows — 0.05 false-positive on both naive and previously-cured women).

Prevalences among VDS presenters come from ``results/vds_etiology.csv``.
Syphilis prevalence in ANC-aged women is taken as 10 %, mid-range from
the calibration baseline nontrep median (~13 % adult female).

    conda run -n starsim python plotting/compute_slide4_ppv.py
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
VDS_CSV = REPO / 'results' / 'vds_etiology.csv'
OUT = REPO / 'results' / 'slide4_diagnostic_performance.csv'

DISEASES = [('ng', 'Gonorrhoea'),
            ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'),
            ('syph', 'Syphilis')]

SENS = {
    ('SOC', 'ng'):   0.50,   # tx_mix: all3 + ngct
    ('SOC', 'ct'):   0.50,   # same routing as NG
    ('SOC', 'tv'):   0.65,   # tx_mix: all3 + mtnz (metronidazole)
    ('SOC', 'syph'): 0.70,   # dual RDT, weighted across active stages
    ('POC', 'ng'):   0.95,   # POC_SENS
    ('POC', 'ct'):   0.95,
    ('POC', 'tv'):   0.95,
    ('POC', 'syph'): 0.90,   # RPR (syph_dx.csv, rows 44-50)
}
SPEC = {
    ('SOC', 'ng'):   0.50,   # tx_mix: mtnz + none
    ('SOC', 'ct'):   0.50,
    ('SOC', 'tv'):   0.35,   # tx_mix: ngct + none
    ('SOC', 'syph'): 0.85,   # dual RDT weighted (naive 0.99 + cured 0.05)
    ('POC', 'ng'):   0.95,   # POC_SPEC
    ('POC', 'ct'):   0.95,
    ('POC', 'tv'):   0.95,
    ('POC', 'syph'): 0.95,   # RPR
}
# Syph prev in ANC-aged women — different pathway, not in vds_etiology.
SYPH_PREV_ANC = 0.10


def main():
    vd = dict(zip(*[pd.read_csv(VDS_CSV)[c] for c in ('metric', 'value')]))
    prev = {'ng':   vd['marg_ng'],
            'ct':   vd['marg_ct'],
            'tv':   vd['marg_tv'],
            'syph': SYPH_PREV_ANC}

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
