"""
Scenario ladders for the POC-diagnostic x demand-side analysis (exp 07 onward).

Three single-axis intensity ladders layered on the POC arm, plus a POC
specificity sweep. Ladders were re-anchored in Nov 2026 after co-author
review (M. Marks: the earlier PN and condom-counselling top rungs were
"a stretch" / "optimistic"; D. Rao: anchor care-seeking multipliers).

PN_INTENSITY
    Notification x attendance by edge type (and partner sex for attendance).
    Effective per-partner reach for the dominant flow (male partner of a
    female index) = notify x attend_m:

        rung       stable   casual   anchor
        baseline    10%      2.5%    patient referral as observed in Zimbabwe:
                                     STICH youth 5.7% of partners treated
                                     (Lariat 2023, SRHM); IPSAZ ANC ~27% of
                                     slip-takers had >=1 partner treated
                                     (Martin 2025, Lancet GH)
        low         18%      5%      best observed patient referral (IPSAZ)
        moderate    32%      11%     SSA patient-referral mean: 53% notify x
                                     25% attend among notified (Taleghani 2019)
        high        51%      23%     provider-assisted referral / EPT-like:
                                     69-84% of notified partners treated in
                                     small SSA studies (Taleghani 2019)

CARE_SEEKING
    Multiplier on symptomatic care-seeking (p_symp_care) for NG/CT/TV and BV,
    applied from 2027 by CareSeekScaler. Female baseline is 0.49 per
    symptomatic episode. Anchored to DHS data for 28 SSA countries (Seidu
    2023, STI): 66% of women with STI symptoms sought care, range 38%
    (Ethiopia) to 86% (Liberia).

        baseline 1.00 -> 0.49    calibrated SOC
        low      1.20 -> 0.59
        moderate 1.40 -> 0.69    ~SSA mean (66%)
        high     1.75 -> 0.86    ~best-performing SSA country (86%)

CONDOM_COUNSELLING  (formerly "bundled prevention")
    Coverage of newly treated people enrolled in a 6-month window of 30%
    lower re-acquisition risk for NG/CT/TV. Effect anchored to Project
    RESPECT (30% fewer incident STIs through 6 months; Kamb 1998, JAMA) and
    the USPSTF review (pooled OR 0.66; Henderson 2020, JAMA). Coverage is the
    only axis.

SPEC_SWEEP
    Per-pathogen POC specificity. Base case 98% (NAAT-based POC; M. Marks).
    95% retained as a pessimistic bound; 99% and 99.5% as optimistic.
"""

# --- Partner notification --------------------------------------------------
PN_INTENSITY = {
    'baseline': dict(
        notify_rates={'stable': 0.20, 'casual': 0.10},
        attendance_rates={'stable': {'f': 0.80, 'm': 0.50},
                          'casual': {'f': 0.50, 'm': 0.25}}),
    'low': dict(
        notify_rates={'stable': 0.30, 'casual': 0.15},
        attendance_rates={'stable': {'f': 0.85, 'm': 0.60},
                          'casual': {'f': 0.55, 'm': 0.35}}),
    'moderate': dict(
        notify_rates={'stable': 0.45, 'casual': 0.25},
        attendance_rates={'stable': {'f': 0.85, 'm': 0.70},
                          'casual': {'f': 0.60, 'm': 0.45}}),
    'high': dict(
        notify_rates={'stable': 0.60, 'casual': 0.35},
        attendance_rates={'stable': {'f': 0.90, 'm': 0.85},
                          'casual': {'f': 0.70, 'm': 0.65}}),
}

# --- Symptomatic care-seeking ---------------------------------------------
CARE_SEEKING = {
    'baseline': 1.00,
    'low':      1.20,
    'moderate': 1.40,
    'high':     1.75,
}

# --- Condom promotion + risk-reduction counselling for the newly treated ---
CONDOM_COUNSELLING = {
    'none':     dict(coverage=0.00, eff=0.30, dur_months=6),
    'low':      dict(coverage=0.25, eff=0.30, dur_months=6),
    'moderate': dict(coverage=0.50, eff=0.30, dur_months=6),
    'high':     dict(coverage=0.75, eff=0.30, dur_months=6),
}
# Back-compat alias for plotting scripts written against the old name.
BUNDLED_PREVENTION = CONDOM_COUNSELLING

# --- POC specificity -------------------------------------------------------
BASE_SPEC = 0.98
SPEC_SWEEP = (0.95, 0.98, 0.99, 0.995)

# Cells re-run at every SPEC_SWEEP value (in addition to the full factorial,
# which is run at BASE_SPEC). (care, pn, cc) tuples.
SPEC_SWEEP_CELLS = (
    ('baseline', 'baseline', 'none'),       # POC alone
    ('high',     'baseline', 'none'),       # each lever alone at high
    ('baseline', 'high',     'none'),
    ('baseline', 'baseline', 'high'),
    ('moderate', 'moderate', 'moderate'),   # all moderate
    ('high',     'high',     'high'),       # all high
)

PN_LEVELS = list(PN_INTENSITY)
CC_LEVELS = list(CONDOM_COUNSELLING)
BP_LEVELS = CC_LEVELS
CARE_LEVELS = list(CARE_SEEKING)
