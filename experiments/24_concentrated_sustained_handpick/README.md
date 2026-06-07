# Exp 24 — Concentrated-sustained hypothesis test (hand-picked)

**Date opened:** 2026-06-07.

**Question.** Can the model produce a **concentrated, sustained**
syphilis epidemic — high prev in FSW (~30%), low prev in general
population (~1%), maintained by an FSW treat-reinfect cycle — under
a single hand-picked, biologically-defensible parameter configuration?

This is a hypothesis test, not a sweep. After exps 22-23 showed that
13-dim blind LHS doesn't land in the data band, the next move is to
pick the configuration we *believe* should produce the right shape
and run it. Either it works (and we open a tight coverage check
around it for HM) or it doesn't (and the diagnosis is that the model
structure can't produce concentrated-sustained syph and we go
deeper).

**Why now.** Exp 23's instrumented re-run confirmed three things:
(1) by-stage shares are roughly right (primary 60-67%, secondary
30-38%, latent <3%), so the disease natural-history isn't the issue;
(2) FSW prevalence varies wildly across sustainers (0% to 83%) — the
"hot 15% basin" is reached via multiple structural pathways including
FSW-extinct draws, which is the opposite of a concentrated epidemic;
(3) the structural pieces for a concentrated-sustained dynamic exist
in the model (FSW pool + clients + RG2 high-risk women + asymmetric
care-seeking), but no single LHS draw activates them together.

User's mental model of how it should work
([[project-syph-calibration-state]]): a small subset of the
population (FSW + RG2 women) cycles infection → visible chancre →
high care-seeking → treatment → reinfection by clients. The men
are the slow-burn reservoir (low care-seeking) that keeps reinfecting
the FSW pool. Most of the general population never sees syphilis —
hence "concentrated."

**Plan — one hand-picked configuration, single sim (3-5 seeds).**

Disease + network parameters (one value, not a prior range):

| Parameter | Value | Rationale |
|---|---|---|
| `syph.beta_m2f` | 0.20 | mid prior (exp 23 prior was log(0.10, 0.35)) |
| `syph.time_to_undetectable` | 20y | Anchor from exp 19/20 |
| `syph.p_symp_primary_f` | 0.50 | High end of (0.10, 0.60) — visibility critical |
| `syph.p_symp_primary_m` | 0.80 | Default — M chancres external, more visible |
| `syph.rel_init_prev` | 0.20 | Baseline |
| `syph_symp_test.rel_test` | 1.30 | Slightly amplified care-seeking |
| `structuredsexual.prop_f0` | 0.55 | More women into non-low-risk |
| `structuredsexual.m1_conc` | 0.20 | Mid-prior |
| `structuredsexual.dur_sw` | 15y | Long: stickier FSW pool |
| `hiv.beta_m2f` | 0.025 | Mid |
| `ng.beta_m2f` / `ct.beta_m2f` / `tv.beta_m2f` | mid-prior | Standard |

Structural / data changes:

- **`anc_probs` restored to defensible ramp**: peak 0.70 by 2018
  scaling to 0.85 by 2030 (away from the PoC 0.20 used in exps
  22-23). Change lives in `interventions.py` as a configurable
  parameter — default switched to realistic; PoC values stay
  available for backward-compat.
- **Boosted care-seeking CSV** at
  `experiments/24_concentrated_sustained_handpick/data/symp_test_prob_concentrated.csv`:
  - FSW (sw=1): **0.65** (from 0.45) — "more attentive to sexual health"
  - RG2 women (sw=0, rg=2): **0.50** (from 0.375)
  - All men: **0.20** (from 0.10) — modestly higher
  - Low-risk women (rg=0/1): **0.15** (unchanged)
- **`rel_trans_latent_half_life`** left at stisim default (12mo).
  Empirically irrelevant per exp 23 follow-up (late latent contributes
  0%); not worth the calibration overhead now.

Diagnostics every run produces (per [[feedback-stage-share-check]]):

- `outputs/results.json` — single-sim summary metrics + targets.
- `outputs/stage_shares.csv` — per-year share of new infections by
  source stage. Reported for the plateau era (2010-2025).
- `figures/timeseries.png` — overall + FSW + general nontrep prev
  through 2040.
- `figures/stage_shares.png` — by-stage transmission share bar chart.
- `figures/subpop_attribution.png` — same FSW/client/general
  breakdown used in exp 23, for direct comparison.

**Success criteria.**

A **primary pass** = all four of the following:

1. FSW prev at 2019 ∈ [0.20, 0.40] (Robyn target 30%, source UNAIDS 2019)
2. nontrep_prevalence_15_64_f at 2016 ∈ [0.004, 0.016] (ZIMPHIA band)
3. Stage shares: primary ∈ [50%, 65%], secondary ∈ [25%, 40%],
   latent ≤ 10% during plateau era
4. Sustained through 2040 (mean new_inf_2030-40 > 0, prev_f_2035-40 ≥ 0.001)

A **diagnostic miss** is also valuable: if (1) misses high, the FSW
pool is too sticky / large; if (1) misses low, the pool is too
loose; if (2) misses high but (1) is in band, general-pop has too
much spillover; if (3) misses on primary share, p_symp_primary or
care-seeking too low.

**Decision branches.**

- **All four pass** → open exp 25 = tight coverage check (50-100 LHS
  draws) over narrow ranges around this configuration to feed HM.
- **(1) and (4) pass but (2) misses high** → iterate by reducing
  general-pop spillover (lower prop_f0, possibly add a partner-rate
  reduction in rg0).
- **(1) misses low** → push longer dur_sw, lower prop_f0 further.
- **(4) misses (extinction)** → the configuration is unsustainable;
  diagnose which sub-population went extinct first and iterate.
- **Multiple misses diffusely** → model can't produce concentrated-
  sustained shape; open exp 25 = structural diagnostic on what's
  pinning the model away from this configuration (e.g. FSW-client
  mixing rate, RG2 contact density).

**What this experiment does NOT do.**

- Does not run HM.
- Does not add new calibration parameters or open new priors.
- Does not change the disease natural-history code (no
  `p_nontrep_revert` or `rel_trans_latent_half_life` opening).
- Does not change network structure — only parameter values within
  existing priors / structures.
