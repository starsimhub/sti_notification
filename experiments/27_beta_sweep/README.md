# Exp 27 — β sweep: find the absolute floor

**Date opened:** 2026-06-07.

**Question.** At exp 24's base config (the configuration that gave
us concentrated-sustained FSW dynamics at the expense of too-high
general spillover), what is the **lowest `syph.beta_m2f`** that
still produces a sustained epidemic — and where does general
nontrep_f land at that floor?

**Why now.** Exp 26 confirmed that network knobs (`m1_conc`,
`prop_f0`) shift WHERE syph lands but not HOW MUCH overall. The
concentration ratio (FSW:gen ≈ 2.7) is structural under the current
network architecture, set by clients' stable-partnership pattern
with non-FSW women. β can't change the ratio either — it scales
both numerator and denominator linearly — but it CAN scale absolute
prevalence levels down toward the loose target band
[[project-syph-calibration-state]].

This experiment finds the model's floor: the lowest sustainable β
and the nontrep_f it produces. The result determines whether the
loose targets (1-3% nontrep_f, 5-10% trep_f) are reachable by
parameter-only knobs, or whether we need to open the structural
lever (marital-MF condom use — deferred).

See [`../26_m1_conc_sweep/SUMMARY.md`](../26_m1_conc_sweep/SUMMARY.md)
for the diagnosis of why network knobs don't move the ratio.

**Plan.**

Sweep `syph.beta_m2f` over **{0.08, 0.10, 0.12, 0.15, 0.20}** —
five values × three seeds = 15 sims, parallelized on 15 workers.
β=0.08 is below the current prior lower bound (0.10); if it lands
in band we'd widen the prior. β=0.20 is the exp 24 baseline.

Everything else at exp 24's hand-pick (verified to give right FSW
dynamics), with **one targeted change** to `time_to_undetectable`:

| Knob | Value | Notes |
|---|---|---|
| `structuredsexual.prop_f0` | 0.55 | exp 24 |
| `structuredsexual.m1_conc` | 0.20 | exp 24 |
| `structuredsexual.client_shares` | 0.20 | exp 24 |
| `structuredsexual.dur_sw` | 15y | exp 24 |
| `syph.p_symp_primary_f` | 0.50 | exp 24 |
| `syph.p_symp_primary_m` | 0.80 | exp 24 |
| `syph_symp_test.rel_test` | 1.30 | exp 24 |
| **`syph.time_to_undetectable`** | **15y** | exp 24 had 20y; shortened so non-trep titre drops below test threshold 5 years sooner — reduces late-latent contribution to nontrep_f stock |
| `syph.rel_init_prev` | 0.20 | exp 24 |
| ANC ramp | defensible (peak 0.70 by 2018) | exp 24 |
| Care-seeking CSV | exp 24's boosted version | exp 24 |

Per [[feedback-stage-share-check]] every sim reports stage shares.

**Success criteria (loose targets per [[project-syph-calibration-state]]):**

A **win** = some β that hits:
- FSW prev 2019 ∈ [0.20, 0.40]
- **nontrep_f 2016 ∈ [0.01, 0.03]** (loose)
- **trep_f 2016 ∈ [0.05, 0.10]** (loose)
- Primary stage share ∈ [0.50, 0.65]
- Secondary stage share ∈ [0.25, 0.40]
- Sustained to 2040

A **diagnostic** = no β satisfies all loose targets but the trend
across the sweep tells us:
- Whether the model floor for nontrep_f at sustainability is below 5%
  (in which case widen the β prior and we have a calibration)
- Or above 5% (in which case parameter-only is exhausted, open the
  marital-MF condom lever)

**Decision branches.**

- **A β value passes loose targets** → open exp 28 = tight LHS
  coverage check around that β value to feed HM.
- **Floor sits at 5-7% nontrep_f when sustained** → the model's
  parameter-only limit. Choice: accept those numbers, or open the
  structural condom lever (exp 28 = client-wife condom test).
- **Sustainability gone at all β** → β prior is mis-specified or
  testing/treatment is over-cleaning. Revisit care-seeking CSV.

**What this experiment does NOT do.**

- Not a full LHS sweep — single parameter.
- Does not change network architecture.
- Does not change condom use, dur_sw, p_symp_primary, or anything
  else from exp 24's hand-pick.
- Does not open new priors.
