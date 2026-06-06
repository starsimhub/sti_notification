"""
Prior distributions for the Zimbabwe calibration of sti_notification.

Nine parameters: five disease betas (HIV, syph, NG, CT, TV), three
network parameters, and the time-to-RPR-undetectable distribution for
late-latent syphilis (added for exp 20 — see
experiments/19_time_to_undetectable_sweep/SUMMARY.md). Condom
effectiveness, rel_trans_primary, rel_init_prev, p_symp, p_symp_care,
and care-seeking rates are *fixed* (set in model.py) per parameter-
engineering analysis (exp 08).

Format: {column_name: (label, low, high, log_scale)}.
"""

import sciris as sc


calib_pars = sc.objdict({
    # HIV
    'hiv.beta_m2f':              ('HIV β (M→F)',           0.005, 0.05,  False),
    # Syphilis
    'syph.beta_m2f':             ('Syph β (M→F)',          0.10,  0.35,  True),
    'syph.time_to_undetectable': ('RPR decline (yrs)',     10,    30,    False),
    # Discharging STIs
    'ng.beta_m2f':               ('NG β (M→F)',            0.02,  0.30,  True),
    'ct.beta_m2f':               ('CT β (M→F)',            0.02,  0.30,  True),
    'tv.beta_m2f':               ('TV β (M→F)',            0.02,  0.60,  True),
    # Network shape
    'structuredsexual.prop_f0':  ('Prop F low-risk',       0.55,  0.90,  False),
    'structuredsexual.m1_conc':  ('M1 concurrency',        0.05,  0.30,  False),
    'structuredsexual.dur_sw':   ('FSW duration (yrs)',     2,     15,    False),
})
