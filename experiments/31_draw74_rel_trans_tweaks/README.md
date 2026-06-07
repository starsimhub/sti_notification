# Exp 31 — Draw 74 + higher rel_trans_primary + half_life=1.2y

**Date opened:** 2026-06-07 (evening).

**Question.** Take exp 30's best draw (draw 74, the 5/7-passer with
FSW=0.337, sustained, stage shares right, but nontrep_f=9.2%
and trep_f=18.7%) and apply three targeted changes — does that
move nontrep_f and trep_f down into their loose bands?

Changes:

1. **`rel_trans_primary = 4`** (up from draw 74's 1.73). Concentrates
   transmission in the short primary window — more FSW reinfections,
   but each lasts less time before treatment, reducing the latent stock
   that drives nontrep_f.
2. **`rel_trans_latent_half_life = 1.2y`** (up from 1.0y). Slightly
   slower latent decay → more sustained transmission floor, which
   may help robustness against the bistability we've been hitting.
3. **stisim code fix**: `set_latent_trans` now uses `rel_trans_secondary`
   as the starting value for the latent decay, rather than a separate
   `rel_trans_latent` parameter. Ensures any increase in
   `rel_trans_secondary` propagates continuously into the latent stage
   (no discontinuity at the secondary→latent boundary). Per Robyn:
   "the rel_trans_ in latency should start at the same level as it
   was during secondary." At defaults (rel_trans_secondary=1,
   rel_trans_latent=1), behavior is unchanged from before.

All other draw 74 parameters held fixed (see config.yaml). 3 seeds,
~3 min wall clock.

**Success criteria.** Same loose targets as exp 30:
- FSW prev 2019 ∈ [0.20, 0.40]
- nontrep_f 2016 ∈ [0.01, 0.03]
- trep_f 2016 ∈ [0.05, 0.10]
- Primary stage share ∈ [0.45, 0.65]
- Secondary stage share ∈ [0.25, 0.45]
- Early latent share ≤ 0.15
- Sustained to 2040

**What this experiment does NOT do.**

- Not a sweep. Single configuration, 3 seeds.
- Does not change network architecture or care-seeking CSV.
- Does not open new priors.
