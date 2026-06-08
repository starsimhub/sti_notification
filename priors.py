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
- exp 32 (2026-06-07): hiv_syph.rel_sus_syph_hiv and
  hiv_syph.rel_trans_syph_hiv. Default 1.0 in stisim — model had
  no mechanism for HIV+ adults to have elevated syph prev beyond
  shared network exposure. ZIMPHIA shows HIV+ trep 3.7× HIV-
  trep; opening these to test whether the HIV→syph coupling
  closes that gap. AIDS variants held at 1.0 (small CD4<200
  population).
- exp 33 (2026-06-07): structuredsexual.fsw_mf_conc_mult. Default
  1.0 in stisim — FSW inherit f2_conc=1.0 for non-commercial
  partnerships. Exp 32's transmission matrix showed F_fsw → M_other
  carries 8% of plateau transmissions (FSW→non-client males), and
  the M_other → F_other downstream amplification keeps general-pop
  prev hot. Lever multiplies FSW MF concurrency; range [0.1, 1.0]
  spans "FSW partner only with clients" to no change. AIDS connector
  variants still held at 1.0.
- exp 34 (2026-06-07): syph.rel_trans_latent_half_life, plus two
  general-pop network levers (structuredsexual.f1_conc and
  structuredsexual.m2_conc). Exp 33 showed the residual gap lives in
  the self-sustaining M↔F general-pop engine — these are the direct
  knobs on it. Half-life governs latent-stage decay (the "long tail"
  of trep+ in the data); f1_conc and m2_conc are the casual
  concurrency rates for medium-risk women and clients (currently
  fixed at 0.15 and 4.4).

Condom effectiveness, p_symp_secondary, p_symp_care, and most
network parameters remain fixed (set in model.py).
"""

import sciris as sc


calib_pars = sc.objdict({
    # HIV
    'hiv.beta_m2f':                 ('HIV β (M→F)',              0.005, 0.05,  False),
    # Syphilis
    'syph.beta_m2f':                    ('Syph β (M→F)',             0.10,  0.35,  True),
    'syph.rel_trans_primary':           ('Primary rel_trans',         1.0,   10.0,  True),
    'syph.rel_trans_latent_half_life':  ('Latent rel_trans half-life (y)', 0.25, 2.0, False),
    'syph.time_to_undetectable':        ('RPR decline (yrs)',        10,    30,    False),
    'syph.p_symp_primary_f':        ('F chancre visible (prob)', 0.10,  0.60,  False),
    'syph.p_symp_primary_m':        ('M chancre visible (prob)', 0.50,  0.95,  False),
    'syph.rel_init_prev':           ('Syph rel init prev',       0.02,  1.00,  True),
    'syph_symp_test.rel_test':      ('Syph symp care-seek mult', 0.30,  1.50,  False),
    # Discharging STIs
    'ng.beta_m2f':                  ('NG β (M→F)',               0.02,  0.30,  True),
    'ct.beta_m2f':                  ('CT β (M→F)',               0.02,  0.30,  True),
    'tv.beta_m2f':                  ('TV β (M→F)',               0.02,  0.60,  True),
    # Network shape
    'structuredsexual.prop_f0':         ('Prop F low-risk',          0.55,  0.90,  False),
    'structuredsexual.m1_conc':         ('M1 concurrency',           0.05,  0.30,  False),
    'structuredsexual.f1_conc':         ('F1 concurrency',           0.05,  0.30,  False),
    'structuredsexual.m2_conc':         ('M2 concurrency',           2.0,   8.0,   False),
    'structuredsexual.dur_sw':          ('FSW duration (yrs)',        2,     15,    False),
    'structuredsexual.fsw_mf_conc_mult':('FSW MF concurrency mult',   0.1,   1.0,   False),
    # HIV-syph coupling (exp 32+)
    'hiv_syph.rel_sus_syph_hiv':    ('HIV→syph rel_sus',          1.0,   3.0,   True),
    'hiv_syph.rel_trans_syph_hiv':  ('HIV→syph rel_trans',        1.0,   2.5,   True),
})
