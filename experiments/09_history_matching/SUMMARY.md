# Exp 09 — History matching: 8 waves

**Date:** 2026-05-19 (initial run); 2026-06-03 (re-run post-ANC fix).

**Question.** Can history matching narrow the 8-parameter prior to a
NROY region consistent with all calibration targets? See
[`../08_coverage_tv_hiv_syphtesting/SUMMARY.md`](../08_coverage_tv_hiv_syphtesting/SUMMARY.md)
for the coverage check and parameter engineering that preceded this.

Re-run required after the ANC serology fix (commit dc951f0) switched
latent syphilis detection from GUD (~5% sensitivity) to RPR/dual RDT
(~90% sensitivity). Pre-fix outputs archived to `outputs/hm_zim_pre_anc_fix`.

**Result.** NROY narrowed from 91% to 1.2% of the prior volume over
8 waves — a ~75x reduction. NG, TV, CT, and HIV betas are well
constrained (69–96% variance reduction). Syphilis beta and the three
network parameters remain unconstrained (14–17% variance reduction).
The syphilis bimodality (sustain/extinct) continues to defeat the
Bayes linear emulator (R² = 0.18–0.25 across 4 attempts), consistent
with the pre-fix run.

![Convergence: NROY fraction per wave.](figures/convergence.png)

![Z-scores across waves. Non-syphilis targets well-centred by wave 8; syphilis targets remain far from target with large spread.](figures/zscores_vs_targets.png)

![Parameter pairplot: waves 1, 4, 8. Betas narrow; network params remain broad.](figures/pairplot.png)

![Constrained dimensions.](figures/constrained_dims.png)

## Wave-by-wave

| Wave | NROY % | Feature emulated | R² | Notes |
|---|---|---|---|---|
| 1 | 91.0% | syph_prev_m_2016 | 0.25 | Syph dominates z-score but emulator can't learn bimodal surface |
| 2 | 16.4% | ng_prev_2005_2015 | 0.99 | NG beta constrained; big NROY cut |
| 3 | 15.5% | syph_prev_m_2016 | 0.18 | Syph emulator still flat |
| 4 | 7.9% | ct_prev_f2530 | 0.94 | CT beta constrained |
| 5 | 8.7% | syph_prev_m_2016 | 0.25 | Syph: no improvement |
| 6 | 2.4% | tv_prev_2005_2015 | 0.99 | TV beta constrained |
| 7 | 2.9% | syph_prev_m_2016 | 0.19 | Syph: still flat |
| 8 | 1.2% | hiv_prev_2010_2020 | 0.93 | HIV beta constrained |

## Parameter constraint (variance reduction vs prior)

| Parameter | Prior range | NROY 90% CI | Var reduction |
|---|---|---|---|
| NG β | [0.02, 0.30] | [0.049, 0.087] | 95.5% |
| TV β | [0.02, 0.60] | [0.051, 0.147] | 90.4% |
| CT β | [0.02, 0.30] | [0.031, 0.111] | 77.8% |
| HIV β | [0.005, 0.05] | [0.006, 0.031] | 68.8% |
| Syph β | [0.10, 0.35] | [0.105, 0.335] | 14.9% |
| prop_f0 | [0.55, 0.90] | [0.568, 0.888] | 16.5% |
| m1_conc | [0.05, 0.30] | [0.061, 0.290] | 15.9% |
| dur_sw | [2, 15] | [2.4, 14.4] | 13.8% |

## Observations

1. **Disease betas well-identified (NG/TV/CT/HIV).** Each has a
   dominant near-orthogonal target that the Bayes linear emulator fits
   well (R² > 0.93). NROY marginals are tight.

2. **Syphilis beta unconstrained by emulation.** The sustain/extinct
   bimodality produces σ² ≈ 0.75 and θ collapsed to the lower bound
   on all dimensions — the emulator sees the bimodal surface as pure
   noise. `syph_prev_m_2016` was selected in 4 of 8 waves by the
   automatic feature selector (highest mean_sq_z ≈ 3300) but never
   achieved R² > 0.25.

3. **Network parameters unconstrained.** `prop_f0`, `m1_conc`, `dur_sw`
   show 14–17% variance reduction — effectively open. Expected from
   sensitivity analysis (ρ < 0.2 for all three).

4. **8000 model evaluations** (1000/wave × 8 waves) in ~135 minutes
   on 75 workers (~18 min/wave).

5. **Comparison to pre-fix run.** Final NROY 1.2% vs 0.85% pre-fix.
   The wider NROY is expected: increased ANC treatment throughput adds
   noise to the syphilis surface, making the emulator slightly more
   conservative. Non-syphilis constraint is comparable.

## Acceptance

The NROY is usable for trajectory selection. Disease betas are
constrained; syphilis and network parameters carry prior uncertainty
forward. Syphilis constraint will happen at the trajectory selection
stage via direct simulation + sustainability filtering + likelihood
weighting, bypassing the emulator entirely.

## Next

- [Trajectory selection](../10_trajectory_selection/README.md): draw
  from NROY, run with seeds, filter extinct syphilis, weight by
  pseudo-likelihood to produce the posterior.
