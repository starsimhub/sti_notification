# Methodology

This document describes *how* the calibration was performed: the
model, the data, the parameter space, the method, the acceptance
criteria, and how the final pipeline came together after several
methodological reversals. For *what* was found and adopted, see
[`calibration_summary.md`](calibration_summary.md). For *how to redo
it*, see [`recalibration_guide.md`](recalibration_guide.md).

## Model

STIsim 1.5.5 / Starsim 3.3.2. Model definition lives in
[`../model.py`](../model.py).

- **Diseases.** HIV, syphilis, NG, CT, TV. A GUD-like placeholder and
  a fetal-health connector (`FetalHealth` + `sti_fetal`) handle
  adverse pregnancy / birth outcomes.
- **Network.** Three-component sexual network: stable (marital),
  casual, and FSW/client. Controlled by `prop_f0` (FSW fraction of
  women), `m1_conc` (general-population concurrency), `m2_conc`
  (client concurrency).
- **Calendar.** Run 1985 → 2040 at quarterly time step.
- **Population scale.** 10,000 agents in the final calibration. Smoke
  runs used 1,500–5,000.
- **Interventions baseline.** ANC syphilis testing with a realistic
  probability ramp 0.05 → 0.90 over 1990 → 2020
  ([`ANC_PROBS_REALISTIC`](../interventions.py)). Symptomatic
  care-seeking ramped per
  [`data/symp_test_prob_concentrated.csv`](../data/). Baseline partner
  notification active at stable 0.20 / casual 0.10 per the
  `SyndromicPN` defaults.

## Data

| Source | What it provides | Locked file |
|---|---|---|
| UNAIDS | Whole-population HIV prevalence + incidence 1990–2040 (projected) | [`data/zimbabwe_hiv_calib.csv`](../data/zimbabwe_hiv_calib.csv) |
| ZIMPHIA 2015–16 | 15–49 HIV prevalence (15.9%); 15–64 syphilis treponemal+ (2.7%) and non-trep+ (0.8%); age × sex syph profile | Inline in scripts + `data/zimphia_2015_syph_table_18_4_A.md` |
| Zimbabwe STI surveillance | NG / CT / TV prevalence 2000–2040 (yearly) | [`data/zimbabwe_sti_data.csv`](../data/zimbabwe_sti_data.csv) |
| Zimbabwe syph surveillance | Syph time series (ANC, FSW survey) | [`data/zimbabwe_syph_data.csv`](../data/zimbabwe_syph_data.csv) |

NG, CT, TV target weights (from prior fits): NG = 2, CT (women 25–30)
= 2, TV = 1. Used as multipliers in the composite pass-count
likelihood (see *Targets and likelihood* below).

## Calibration parameters

19 parameters opened up in the final ensemble (exp 40). Full list:

| Parameter | Role | Prior range / type |
|---|---|---|
| `hiv.beta_m2f` | HIV transmission | log-uniform |
| `syph.beta_m2f` | Syph transmission | log-uniform |
| `ng.beta_m2f` | NG transmission | log-uniform |
| `ct.beta_m2f` | CT transmission | log-uniform (widened in exp 40) |
| `tv.beta_m2f` | TV transmission | log-uniform |
| `rel_sus_syph_hiv` | HIV+ susceptibility to syph | uniform on log-scale |
| `rel_trans_syph_hiv` | HIV+ transmissibility of syph | uniform on log-scale |
| `hiv.rel_init_prev` | HIV 1985 seed multiplier | uniform [0.3, 1.5] |
| `prop_f0` | FSW fraction | uniform |
| `m1_conc` | General-pop concurrency | uniform |
| `m2_conc` | Client concurrency | uniform |
| `time_to_undetectable` | Late-latent → undetectable | uniform on log-scale, years |
| `rel_trans_primary` | Primary stage transmissibility multiplier | uniform |
| `stable_act_decay` | Per-year coital decay on stable edges | uniform |
| `client_marital_act_mult` | Client-husband marital-act multiplier | uniform |
| 4 others | Tightening priors that survived parameter engineering | various |

Held *fixed* throughout: condom effectiveness; `p_symp` per disease;
`p_symp_care = 0.75`; symptomatic care-seeking rates from CSV. The
rationale is that these are observable or have strong evidence in the
literature and would not be jointly identifiable from prevalence
alone.

The parameter list evolved across the experiments (8 → 9 → 18 → 19);
the engineering log is in [`assumptions.md`](assumptions.md) and the
per-experiment SUMMARYs on `archive/calibration-2026-06`.

## Targets and likelihood

The calibration uses a **composite pass-count target structure**
rather than a full likelihood. Each draw is evaluated against ~9
target bands derived from the data:

| Target | Band | Time point |
|---|---|---|
| `nontrep_band` | [0.01, 0.05] | 2016, F 15–64 |
| `trep_band` | [0.02, 0.06] | 2016, F 15–64 |
| `fsw_band` | [0.20, 0.40] | 2019 |
| HIV+/HIV− syph trep ratio | [3.0, 6.0] | 2016 |
| HIV whole-pop | [0.09, 0.13] | 2010–2020 mean |
| Syph primary share of new infections | ~0.40–0.70 | 2010–2020 mean |
| Syph secondary share | ~0.20–0.40 | 2010–2020 mean |
| Syph early-latent share | ~0.05–0.15 | 2010–2020 mean |
| Sustainability | new_infections > 0 over 2030–2040 | endpoint check |

For the final ensemble, a draw is **accepted** if it sustains in all
3 seeds AND its mean `n_pass` across seeds is ≥ 4 of the 9 targets.
Why a pass-count rather than a likelihood: most targets are *bands*
with sharp ZIMPHIA / UNAIDS edges, not point estimates with known
variance; squared-error Gaussian likelihoods on band targets produced
degenerate ESS in trajectory selection (exp 09, 18). Pass-count is
robust to the structural ceiling — if a target band is unreachable,
draws closest to it still survive the filter via the other 8.

For full discussion of likelihood vs pass-count trade-off and the
trajectory-selection experiments that motivated this switch, see
exp 09, exp 18, exp 20 SUMMARYs on `archive/calibration-2026-06`.

## Method evolution (chronological)

The final method was *not* the first method. Three distinct
methodological phases:

### Phase A. Prior predictive coverage check (exp 01–08)

100 → 150 → 300 prior draws, single seed, raw prevalence target. The
syphilis arm extincted across all draws. Root-caused to **seeding**
(not enough initial syph cases at 5k agents). Fixed seeding, doubled
to 10k agents: 33/100 sustained, 11/100 reached the ~2% data target.
Coverage check passed *only after* correcting the target mapping to
detectable (RDT-observable) prevalence, not raw.

### Phase B. History matching + Bayes-linear emulation (exp 09–20)

Eight HM waves on 8 parameters reduced the prior volume by 99% to a
1.2% NROY region (exp 09). Trajectory selection on the NROY ensemble
produced ESS = 75.6 (8.3%) — usable for HIV, NG, CT, TV but the
syphilis arm hit a **structural failure**: the model produced a
massive early epidemic (~14% peak ~1987) then burned through the
susceptible pool to near-zero by 2005.

The decision then was: was syph's behaviour a *dynamics* problem or
an *observability* problem? Exp 16 / 17 patched the observability
layer (detectable vs raw prevalence). Exp 20 re-ran HM on the patched
stisim with a 9th parameter (`time_to_undetectable`) opened, reaching
0.99% NROY and ESS = 68.0 (7.0%) — but trajectory selection revealed
all top draws still **decay through the 2016 target**. The
calibration was finding cross-section fits without endemic
equilibrium. Bayes-linear emulation could not handle the
sustained/decay bimodality (R² ≤ 0.25 on syphilis-related summaries).

### Phase C. LHS + robust-ensemble filtering (exp 22–41)

Method switch: abandon emulation, run large LHS sweeps directly, use
3-seed re-run as the robustness filter. Pipeline:

1. **Phase 1.** LHS over 14 → 16 → 18 → 19 parameters; 300 → 1,500 →
   5,000 draws single-seed. Pass filter: sustained at 2040 AND
   `n_pass` ≥ 5 of 9 targets → ~300 candidates.
2. **Phase 2.** Re-run candidates with 3 seeds. Robustness filter:
   sustained in all 3 seeds AND mean `n_pass` ≥ 4 → ~200 robust
   draws.
3. **Publication extraction.** Re-simulate the 200 × 3 = 600 sims,
   save annualised time series + 2016/2020 age × sex snapshots,
   compute ensemble quantiles, generate figures.

Final ensemble: exp 40 (parameter LHS) + exp 41 (publication figures).
The LHS approach surfaced the structural ceiling on syphilis absolute
prevalence (none of the 20-dimensional sweeps recovered the ZIMPHIA
2.7%) and the structural identifiability of the HIV–syph coupling
(rel_sus / rel_trans levers brought the HIV+/HIV− trep ratio into band
at 90% pass rate).

## Acceptance criteria

A draw is **accepted** into the final ensemble iff:

1. Sustained transmission in all 3 seeds (new syph infections > 0
   during 2030–2040 in each).
2. Mean `n_pass` ≥ 4 of 9 targets.

The ensemble as a whole is **acceptable** for downstream PN scenario
analysis iff:

1. HIV whole-pop median in UNAIDS band for ≥ 50% of years 2010–2020.
2. HIV+/HIV− syph trep ratio in [3.0, 6.0] for ≥ 80% of draws.
3. Syph stage shares (primary / secondary / early latent) in the
   ~55/35/10 expert-prior band for ≥ 90% of draws.
4. NG median in surveillance band for 2010+.

The final ensemble passed all four. Syph and CT *absolute* prevalence
were exempt — the syph levels overshoot is documented as a structural
ceiling, the CT levels overshoot is documented as a weak fit
acceptable for PN scenarios but flagged for diagnosis if CT-specific
claims are added.

## Software stack

- **Starsim** 3.3.2.
- **STIsim** 1.5.5, with two extension branches required for the final
  ensemble:
  - `feat/partner-notification-network` (PR #457) — `PartnerNotification`
    API used by `SyndromicPN` in [`../interventions.py`](../interventions.py).
  - `feat/marital-act-decay` — `stable_act_decay` and
    `client_marital_act_mult` mechanisms added in exp 40.
  - `feat/syph-detectable-state` — `detectable_prevalence` result
    added during the exp 16/17 observability fix.
- **Python** 3.11, conda env `starsim`.
- **Compute.** IDM Azure VM ("Applied Math" subscription), 24-core
  batch parallelism via `multiprocessing.Pool`.

See [`recalibration_guide.md`](recalibration_guide.md) for the exact
environment recipe.
