"""
Prior distributions for the Zimbabwe calibration of sti_notification.

Format: {column_name: (label, low, high, log_scale)}.

Parameters opened over time:
- exp 17-20: disease betas (HIV, syph, NG, CT, TV), network shape
  (prop_f0, m1_conc, dur_sw), time_to_undetectable.
- exp 22: syph.p_symp_primary_f/m, syph_symp_test.rel_test —
  care-seeking knobs.
- exp 23: syph.rel_init_prev — initial-condition sensitivity.
- exp 29 (2026-06-07): syph.rel_trans_primary — primary-stage
  transmissibility multiplier. Robyn: previous work set this at
  ~5; opening for calibration to test concentrated-sustained
  hypothesis where primary-stage dominates transmission.

Condom effectiveness, p_symp_secondary, p_symp_care, and most
network parameters remain fixed (set in model.py).
"""

import sciris as sc


calib_pars = sc.objdict({
    # HIV
    'hiv.beta_m2f':                 ('HIV β (M→F)',              0.005, 0.05,  False),
    # Syphilis
    'syph.beta_m2f':                ('Syph β (M→F)',             0.10,  0.35,  True),
    'syph.rel_trans_primary':       ('Primary rel_trans',         1.0,   10.0,  True),
    'syph.time_to_undetectable':    ('RPR decline (yrs)',        10,    30,    False),
    'syph.p_symp_primary_f':        ('F chancre visible (prob)', 0.10,  0.60,  False),
    'syph.p_symp_primary_m':        ('M chancre visible (prob)', 0.50,  0.95,  False),
    'syph.rel_init_prev':           ('Syph rel init prev',       0.02,  1.00,  True),
    'syph_symp_test.rel_test':      ('Syph symp care-seek mult', 0.30,  1.50,  False),
    # Discharging STIs
    'ng.beta_m2f':                  ('NG β (M→F)',               0.02,  0.30,  True),
    'ct.beta_m2f':                  ('CT β (M→F)',               0.02,  0.30,  True),
    'tv.beta_m2f':                  ('TV β (M→F)',               0.02,  0.60,  True),
    # Network shape
    'structuredsexual.prop_f0':     ('Prop F low-risk',          0.55,  0.90,  False),
    'structuredsexual.m1_conc':     ('M1 concurrency',           0.05,  0.30,  False),
    'structuredsexual.dur_sw':      ('FSW duration (yrs)',        2,     15,    False),
})
