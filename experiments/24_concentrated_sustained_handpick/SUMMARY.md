# Exp 24 — Concentrated-sustained hypothesis test (hand-picked v1)

**Date:** 2026-06-07.

**Question.** Can a single hand-picked, biologically-defensible
parameter configuration produce a concentrated-sustained syphilis
epidemic — FSW prev ~30%, general nontrep_f ~1%, sustained — with
the model as currently structured?

**Result.** **4 of 5 targets pass; spillover from FSW to general
population is the diagnostic miss.** 3-seed means:

| Target | Value | Range | Status |
|---|---|---|---|
| FSW prev 2019 | 0.40 | [0.20, 0.40] | ✓ PASS (at ceiling) |
| Primary stage share (plateau) | 0.63 | [0.50, 0.65] | ✓ PASS |
| Secondary stage share (plateau) | 0.35 | [0.25, 0.40] | ✓ PASS |
| Sustained to 2040 | yes | new_inf > 0 | ✓ PASS |
| **nontrep_f 2016** | **0.151** | [0.004, 0.016] | ✗ MISS (~10× high) |

Plus context:
- trep_f 2016 = 0.237 (Robyn target ~4-5%)
- client prev 2016 = 0.343
- overall prev_f 2016 = 0.121

## Observations

1. **FSW dynamics work as intended.** Concentrated, sustained, at
   the data ceiling. Long `dur_sw=15y` + boosted FSW care-seeking
   (CSV 0.65) + p_symp_primary_f=0.50 produces a clean treat-reinfect
   cycle.
2. **Stage shares match Robyn's target.** Primary 63%, secondary 35%,
   latent <3% — no need to touch latent transmission parameters.
3. **The model has a BIG spillover from FSW/clients to general
   population.** Clients sit at 34% prev (matching their FSW partners),
   and the bridge from clients to general F sustains a 12% prev in
   the bulk of women.
4. **`prop_f0 = 0.55` was a wrong-direction call.** Putting only
   55% of women in the lowest-risk pool means 45% are in higher-risk
   pools that bridge to clients. The correction is to push `prop_f0`
   HIGHER (insulate most women in rg0), not lower.
5. **`m1_conc = 0.20` is too high.** It gives mid-risk men concurrency
   on the order of FSW clients, sustaining a bridge to general F.

## Acceptance

The structural framing (concentrated-sustained as a treat-reinfect
cycle on a small subset) is validated by the FSW + stage results.
The bridge to general population needs to be thinned. Direction is
clear; next experiment iterates three specific knobs.

## Next

[Done — see `../25_concentrated_v2_lower_spillover/`]
Iterate `prop_f0` UP (0.55 → 0.85), `m1_conc` DOWN (0.20 → 0.05),
and `client_shares` DOWN (0.20 → 0.15) to thin the FSW-to-general
bridge. Hold everything else fixed. Expectation: nontrep_f drops
~5-10×, FSW prev stays in band, stage shares stay primary-dominant.

Also adds Robyn's refined target: **trep_f overall ~4-5%** (up from
ZIMPHIA's 2.7% baseline because of reporting concerns), with higher
prevalence in key groups (FSW, PLHIV, >5 partners).

## Artifacts

- `outputs/results.json` — per-seed + mean summary metrics
- `outputs/stage_shares.csv` — by-year stage attribution
- `outputs/series.pkl` — time series per seed
- `run.py` — single-config driver
- `data/symp_test_prob_concentrated.csv` — care-seeking CSV with
  boosted FSW (0.65) + RG2 women (0.50) + men (0.20)
