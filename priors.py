"""
Prior distributions for the Zimbabwe calibration of sti_notification.

Eight parameters total: five disease betas (HIV, syph, NG, CT, TV) and three
network parameters governing risk-group structure and concurrency. Condom
effectiveness, p_symp, p_symp_care, and care-seeking rates are *fixed* (set
in model.py) per the project decision; only beta + network shape are opened
up here.

Format: {column_name: (label, low, high, log_scale)}.
Bounds inherited where reasonable from the prior stisim_vddx_zim Optuna run
(STIsim 1.4 / 1.5.2) and widened for joint history-matching against current
STIsim 1.5.5 dynamics.
"""

import sciris as sc


calib_pars = sc.objdict({
    # HIV
    'hiv.beta_m2f':             ('HIV β (M→F)',          0.002, 0.014, False),
    'hiv.rel_init_prev':        ('HIV rel. init prev',   2,    15,     False),
    # Syphilis
    'syph.beta_m2f':            ('Syph β (M→F)',         0.01,  0.35,  True),
    'syph.rel_trans_primary':   ('Syph rel trans primary', 3,   10,    False),
    'syph.eff_condom':          ('Syph condom eff',      0.30,  0.70,  False),
    # Discharging STIs
    'ng.beta_m2f':              ('NG β (M→F)',           0.02,  0.30,  True),
    'ct.beta_m2f':              ('CT β (M→F)',           0.02,  0.30,  True),
    'tv.beta_m2f':              ('TV β (M→F)',           0.02,  0.30,  True),
    # Network shape
    'structuredsexual.prop_f0': ('Prop F low-risk',      0.55,  0.90,  False),
    'structuredsexual.m1_conc': ('M1 concurrency',       0.05,  0.30,  False),
})
