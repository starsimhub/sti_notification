"""
Scenario ladders for the STI undertreatment analysis.

Two single-axis intensity ladders, layered on top of each calibrated draw
(POC arm):

  PN_INTENSITY        partner-notification intensity. One axis that co-varies
                      notification and attendance from the SOC baseline up to a
                      plausible maximum. Each level is a pn_pars dict consumed
                      directly by interventions.make_pn (notify_rates by edge
                      type; attendance_rates by edge type x partner sex).

  CARE_SEEKING        symptomatic care-seeking intensity. One axis = a scalar
                      multiplier on NG/CT/TV symptomatic care-seeking
                      (p_symp_care), passed to make_sim(care_seek_mult=...).
                      Scales the VDS (discharging-STI) pathway only.

  BUNDLED_PREVENTION  "bundled prevention" is just the slide label for the
                      rel_sus reduction we already use (CondomCounseling, now in
                      interventions.py). One axis = coverage of treated agents
                      enrolled; per-person effect (rel_sus reduction) and
                      duration fixed. These dicts are the args for that
                      intervention. No new class.

These three ladders are the factors of the POC factorial (run_scenarios.py).
Levels are intentionally round for slide use. All are provisional pending the
sustained recalibrated ensemble.
"""

# --- Partner-notification intensity (single axis: notify + attend together) ---
PN_INTENSITY = {
    'baseline': dict(
        notify_rates={'stable': 0.20, 'casual': 0.10},
        attendance_rates={'stable': {'f': 0.80, 'm': 0.50},
                          'casual': {'f': 0.50, 'm': 0.25}}),
    'low': dict(
        notify_rates={'stable': 0.35, 'casual': 0.25},
        attendance_rates={'stable': {'f': 0.85, 'm': 0.60},
                          'casual': {'f': 0.60, 'm': 0.40}}),
    'moderate': dict(
        notify_rates={'stable': 0.55, 'casual': 0.45},
        attendance_rates={'stable': {'f': 0.90, 'm': 0.70},
                          'casual': {'f': 0.70, 'm': 0.55}}),
    'high': dict(
        notify_rates={'stable': 0.75, 'casual': 0.65},
        attendance_rates={'stable': {'f': 0.92, 'm': 0.80},
                          'casual': {'f': 0.80, 'm': 0.70}}),
    'maximum': dict(
        notify_rates={'stable': 0.90, 'casual': 0.90},
        attendance_rates={'stable': {'f': 0.95, 'm': 0.90},
                          'casual': {'f': 0.90, 'm': 0.85}}),
}

# --- Symptomatic care-seeking (single axis: care_seek_mult) ---
# Scalar multiplier on NG/CT/TV symptomatic care-seeking (p_symp_care), applied
# via make_sim(care_seek_mult=...). baseline=1.0 is the calibrated SOC level;
# female care-seeking saturates (clips to 1.0) near mult~2. Scales the VDS
# (discharging-STI) pathway only; syph symptomatic testing stays at baseline.
CARE_SEEKING = {
    'baseline': 1.0,
    'low':      1.25,
    'moderate': 1.5,
    'high':     1.8,
    'maximum':  2.2,
}

# --- Bundled prevention for the diagnosed (single axis: coverage) ---
# eff = per-person reduction in re-acquisition (rel_sus) of ng/ct/tv while
# enrolled; dur_months = protection window. Fixed across levels so coverage is
# the only axis.
BUNDLED_PREVENTION = {
    'none':     dict(coverage=0.00, eff=0.50, dur_months=6),
    'low':      dict(coverage=0.25, eff=0.50, dur_months=6),
    'moderate': dict(coverage=0.50, eff=0.50, dur_months=6),
    'high':     dict(coverage=0.75, eff=0.50, dur_months=6),
    'maximum':  dict(coverage=1.00, eff=0.50, dur_months=6),
}

PN_LEVELS = list(PN_INTENSITY)
BP_LEVELS = list(BUNDLED_PREVENTION)
CARE_LEVELS = list(CARE_SEEKING)
