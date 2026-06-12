# Exp 01 pilot — SUMMARY (v2: NG-fix + expanded endpoints)

**Scale.** 10 draws × 3 seeds × 9 arms = 270 sims.
Counts over 2027-2040, scaled to Zimbabwe population (~8.7M). All "M" values are millions of events/infections; "K" is thousands.

## Headline

**Demand generation is the dominant lever for NG/CT/TV.** PN intensity (B→C3) and FSW outreach (D) together produce modest impact (~10% relative reduction in NG/CT/TV prev vs POC baseline). Symptomatic-care-seeking ×2 (E2) more than triples that gain. The E arms (`E1_d_careseek_1_5x`, `E2_d_careseek_2x`, `E3_d_careseek_3x`) stack a care-seeking multiplier on the full D intervention package; ×3 is a clipped ceiling (all rates except TV M saturate at 1.0). Syph and BV are unaffected: syph care-seeking is governed by `symp_test_prob.csv`, not the NG/CT/TV `p_symp_care` lever; BV is in a stable equilibrium at ~40% prev.

Arms (all start from the calibrated baseline; intv_year=2027):

  - **A** SOC: syndromic NG/CT/TV + syndromic syph + baseline PN.
  - **B** POC: POC etiological NG/CT/TV + POC syph (gud2) + baseline PN.
  - **C1/C2/C3** POC + PN 1.5/2/3× baseline rates.
  - **D** C3 + direct FSW NG/CT/TV outreach (~70%/yr reach).
  - **E1/E2/E3** D + symptomatic care-seeking ×1.5/2/3 (applied equally to F and M, clipped to 1.0).

Wiring check on the symptomatic→PN pipeline (run before E arms were added): symptomatic NG men → `syndromic_uds` (90% presumptive NG tx under SOC) or `POCPanel` (95% sens under POC) → PN index pool → notify partners → female partners routed through `syndromic_vds` (SOC) or `POCPanel` (POC). Bounded by symptomatic care-seeking (~54% of NG men ever caught at care = 65% symp × 83% care), PN attendance (stable F 80%, casual M 25% at baseline), and asymptomatic transmission chains via the FSW reservoir.

Endpoints added this iteration:
  - **BV prevalence + counts** (`sim.results.bv`). Surfaced because BV is the dominant cause of VDS-like presentations (~40% prev in women, equilibrium) and drives unnecessary syndromic NG/CT/TV treatment under SOC.
  - **Wasted PN attendance**: PN attendees who had no current STI (NG/CT/TV/syph all negative at attendance). BV is excluded — not sexually transmitted, so PN triggered by BV-driven over-treatment is wasted by definition. Counts the clinic-time and partner-relationship cost of false-alarm PN.

Effects (A baseline → C3 dx+PN → D adds FSW outreach → E2 adds 2× care-seeking):
  - **NG point-prevalence at 2040:** 0.7% (A) → 0.9% (C3) → 0.8% (D) → 0.5% (E2). E2 vs A: -29% relative.
  - **CT point-prevalence at 2040:** 9.8% (A) → 9.3% (C3) → 8.8% (D) → 7.4% (E2). E2 vs A: -24% relative.
  - **TV point-prevalence at 2040:** 12.3% (A) → 10.1% (C3) → 9.5% (D) → 8.2% (E2). E2 vs A: -34% relative.
  - **Syph sexually-transmissible prevalence at 2040** (primary + secondary + early latent — WHO early infectious syphilis): 3.7% (A) → 3.8% (B) → 3.5% (C3) → 3.6% (D) → 2.2% (E2) → 1.3% (E3). E3 vs A: -64% relative. The E-arms care-seeking multiplier scales syph symp_test_prob in addition to NG/CT/TV `p_symp_care` — so syph finally responds to demand-gen, in contrast to the earlier flat C3→D→E2 (where E only scaled NG/CT/TV). Total syph prev not reported — the calibration ensemble overshoots total syph prev (latent/tertiary), so the policy-relevant slice is the sexually-transmissible fraction.
  - **Unnecessary syph treatments A→B:** 5.27M → 0.41M (-92%) — POC dx specificity win still clean.
  - **BV prevalence at 2040 (all arms):** ~40.2%. BV is the dominant cause of VDS presentations — most women presenting with VDS-like symptoms in this model have BV, not NG/CT/TV. Under SOC syndromic management they get presumptively treated for NG/CT/TV and become PN indices.
  - **PN false-alarm indices (A):** 7.10M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (B):** 0.64M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (C3):** 0.83M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (D):** 1.01M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (E2):** 1.69M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **Wasted PN attendance:** 0.13M / 1.01M (12.6%) in A vs 1.21M / 5.82M (20.7%) in E3. Scaling PN volume reaches further into casual partnerships with lower STI co-prev → wasted-fraction creeps up.

Per-episode "treated within 3 months of acquisition" metric (`CareTimingAnalyzer`): much stricter than the lax `tx_success/new_inf` event-ratio (which double-counts re-infections + pre-window cures). Compare A vs E3:
  - **NG:** A lax 23.5% → strict 22.1% ; E3 lax 31.8% → strict 28.6%.
  - **CT:** A lax 43.7% → strict 9.7% ; E3 lax 64.4% → strict 43.6%.
  - **TV:** A lax 5.6% → strict 4.2% ; E3 lax 29.9% → strict 22.4%.
  - **SYPH:** A lax 84.5% → strict 31.3% ; E3 lax 105.0% → strict 57.0%.

**Syph APO:** stisim's `new_congenital` ~33-36K cases per arm; `new_nnds` and `new_stillborns` are placeholder fields never written without FetalHealth wiring.

## Per-disease summary, by arm

Mean over draws+seeds. All counts in millions over 2027-2040.
`prop_treated` = `tx_success / new_inf` is the share of new infections that ended up cleared by a treatment. `prev_end` is point-prevalence at sim end (2040).

### SYPH
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 3.46M | 3.08M | 3.19M | 3.23M | 3.47M | 3.49M | 2.32M | 2.62M | 1.80M |
|   new inf — F | 1.76M | 1.61M | 1.68M | 1.72M | 1.87M | 1.85M | 1.19M | 1.28M | 0.80M |
|   new inf — M | 1.70M | 1.46M | 1.50M | 1.51M | 1.60M | 1.63M | 1.13M | 1.35M | 1.00M |
| Treatments — total | 8.17M | 2.73M | 2.93M | 3.08M | 3.41M | 3.43M | 2.77M | 3.31M | 2.99M |
|   successful | 2.65M | 2.25M | 2.42M | 2.53M | 2.80M | 2.82M | 1.96M | 2.30M | 1.64M |
|   unnecessary | 5.27M | 0.41M | 0.44M | 0.48M | 0.52M | 0.53M | 0.75M | 0.94M | 1.29M |
| n_infected (point, 2040) | 1865.3K | 1884.2K | 1826.4K | 1759.7K | 1735.6K | 1735.0K | 1114.8K | 1056.9K | 683.0K |
| Sexually transmissible prev (point, 2040) | 3.7% | 3.8% | 3.6% | 3.3% | 3.5% | 3.6% | 2.3% | 2.2% | 1.3% |
| Prop new inf treated (event-ratio, lax) | 84.5% | 73.0% | 75.7% | 78.4% | 80.8% | 80.8% | 84.5% | 87.5% | 105.0% |
|   — F | 89.6% | 82.6% | 86.2% | 89.4% | 91.2% | 88.9% | 91.1% | 91.8% | 113.1% |
|   — M | 77.4% | 61.8% | 63.4% | 65.4% | 68.2% | 71.1% | 77.1% | 82.8% | 96.0% |
| Prop new inf cured w/in 3mo (per-episode, strict) | 31.3% | 32.0% | 32.9% | 33.0% | 34.0% | 33.8% | 40.2% | 47.2% | 57.0% |

### NG
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 4.84M | 7.61M | 7.49M | 7.27M | 7.13M | 6.41M | 4.81M | 4.19M | 3.81M |
|   new inf — F | 2.26M | 3.47M | 3.44M | 3.36M | 3.31M | 3.10M | 2.26M | 1.99M | 1.79M |
|   new inf — M | 2.59M | 4.15M | 4.05M | 3.92M | 3.82M | 3.31M | 2.56M | 2.20M | 2.02M |
| Treatments — total | 9.93M | 2.10M | 2.18M | 2.23M | 2.34M | 2.37M | 2.39M | 2.42M | 2.46M |
|   successful | 1.13M | 1.43M | 1.47M | 1.48M | 1.53M | 1.47M | 1.32M | 1.24M | 1.16M |
|   unnecessary | 8.76M | 0.61M | 0.66M | 0.69M | 0.75M | 0.84M | 1.01M | 1.14M | 1.25M |
| n_infected (point, 2040) | 103.2K | 163.4K | 157.7K | 151.9K | 142.0K | 127.5K | 88.7K | 73.5K | 70.2K |
| Prevalence (point, 2040) | 0.7% | 1.1% | 1.0% | 1.0% | 0.9% | 0.8% | 0.6% | 0.5% | 0.5% |
| Prop new inf treated (event-ratio, lax) | 23.5% | 19.1% | 19.8% | 20.6% | 21.7% | 23.5% | 27.8% | 29.6% | 31.8% |
|   — F | 6.2% | 8.9% | 10.6% | 12.2% | 14.4% | 19.1% | 22.8% | 25.6% | 27.9% |
|   — M | 38.1% | 27.3% | 27.2% | 27.4% | 27.5% | 27.5% | 32.1% | 33.1% | 35.3% |
| Prop new inf cured w/in 3mo (per-episode, strict) | 22.1% | 17.6% | 18.0% | 18.6% | 19.2% | 20.5% | 24.6% | 26.2% | 28.6% |

### CT
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 14.80M | 19.09M | 18.90M | 18.75M | 18.45M | 17.96M | 17.35M | 17.23M | 17.14M |
|   new inf — F | 8.10M | 8.77M | 8.77M | 8.77M | 8.74M | 8.75M | 8.40M | 8.56M | 8.48M |
|   new inf — M | 6.70M | 10.33M | 10.14M | 9.99M | 9.72M | 9.22M | 8.96M | 8.69M | 8.67M |
| Treatments — total | 9.93M | 7.32M | 7.63M | 7.93M | 8.34M | 8.75M | 10.11M | 10.65M | 10.82M |
|   successful | 5.91M | 6.32M | 6.56M | 6.80M | 7.13M | 7.43M | 8.55M | 8.95M | 8.99M |
|   unnecessary | 3.38M | 0.30M | 0.34M | 0.37M | 0.43M | 0.50M | 0.61M | 0.71M | 0.82M |
| n_infected (point, 2040) | 1537.0K | 1590.0K | 1556.0K | 1520.8K | 1471.8K | 1381.5K | 1219.5K | 1174.1K | 1155.3K |
| Prevalence (point, 2040) | 9.8% | 10.1% | 9.9% | 9.7% | 9.3% | 8.8% | 7.7% | 7.4% | 7.3% |
| Prop new inf treated (event-ratio, lax) | 43.7% | 36.4% | 38.1% | 39.7% | 42.2% | 47.8% | 58.3% | 61.6% | 64.4% |
|   — F | 17.5% | 23.7% | 27.5% | 30.8% | 35.4% | 46.0% | 57.7% | 62.0% | 66.1% |
|   — M | 75.8% | 47.3% | 47.4% | 47.8% | 48.5% | 49.4% | 58.1% | 61.1% | 63.0% |
| Prop new inf cured w/in 3mo (per-episode, strict) | 9.7% | 28.3% | 28.6% | 28.9% | 29.5% | 31.3% | 38.1% | 41.7% | 43.6% |

### TV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 44.19M | 44.93M | 44.48M | 44.15M | 43.48M | 41.94M | 40.68M | 39.92M | 38.88M |
|   new inf — F | 11.61M | 11.81M | 12.26M | 12.64M | 13.15M | 13.52M | 13.45M | 13.57M | 13.66M |
|   new inf — M | 32.61M | 33.14M | 32.24M | 31.54M | 30.35M | 28.45M | 27.25M | 26.37M | 25.24M |
| Treatments — total | 3.56M | 6.25M | 6.57M | 6.86M | 7.26M | 7.42M | 9.18M | 10.78M | 12.39M |
|   successful | 2.06M | 4.96M | 5.23M | 5.45M | 5.77M | 5.84M | 7.29M | 8.64M | 10.09M |
|   unnecessary | 1.28M | 0.73M | 0.77M | 0.80M | 0.86M | 0.93M | 1.09M | 1.19M | 1.19M |
| n_infected (point, 2040) | 1930.2K | 1802.6K | 1734.6K | 1676.5K | 1587.4K | 1492.1K | 1373.6K | 1279.2K | 1154.2K |
| Prevalence (point, 2040) | 12.3% | 11.5% | 11.1% | 10.7% | 10.1% | 9.5% | 8.8% | 8.2% | 7.4% |
| Prop new inf treated (event-ratio, lax) | 5.6% | 12.1% | 13.1% | 13.8% | 15.0% | 16.8% | 22.0% | 26.1% | 29.9% |
|   — F | 16.0% | 18.6% | 21.2% | 23.2% | 26.2% | 31.2% | 39.8% | 46.1% | 47.0% |
|   — M | 1.2% | 9.4% | 9.5% | 9.6% | 9.8% | 9.8% | 13.0% | 15.8% | 20.9% |
| Prop new inf cured w/in 3mo (per-episode, strict) | 4.2% | 9.7% | 10.0% | 10.3% | 10.7% | 11.4% | 15.3% | 18.8% | 22.4% |

### BV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 78.91M | 75.99M | 76.72M | 77.27M | 78.00M | 78.30M | 81.71M | 84.26M | 84.69M |
|   new inf — F | 78.97M | 76.05M | 76.77M | 77.33M | 78.06M | 78.35M | 81.77M | 84.31M | 84.74M |
|   new inf — M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M |
| Treatments — total | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   successful | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   unnecessary | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| n_infected (point, 2040) | 10730.3K | 10770.9K | 10759.8K | 10751.0K | 10741.7K | 10743.0K | 10716.3K | 10694.6K | 10717.9K |
| Prevalence (point, 2040) | 40.2% | 40.4% | 40.3% | 40.2% | 40.2% | 40.2% | 40.0% | 39.8% | 39.9% |
| Prop new inf treated (event-ratio, lax) | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   — F | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   — M | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| Prop new inf cured w/in 3mo (per-episode, strict) | NA | NA | NA | NA | NA | NA | NA | NA | NA |

## Syph APO/ABO

Native syph module results, summed over 2027-2040.

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| Congenital syph cases | 35.6K | 37.5K | 38.9K | 37.0K | 37.2K | 40.0K | 22.6K | 23.2K | 15.1K |
| Congenital deaths (=NND+stillborn) | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Neonatal deaths (NND)* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Stillbirths* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |

*\* NND/stillborn rely on `FetalHealth` to fire ti_nnd / ti_stillborn. Without FetalHealth wired (this pilot), those are 0 across all arms.*

## HIV + partner notification

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| HIV new infections | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.51M | 0.51M |
| PN partners notified | 1.58M | 1.63M | 2.32M | 2.98M | 4.28M | 4.44M | 5.26M | 5.69M | 6.26M |
| PN partners attending | 1.01M | 1.03M | 1.91M | 2.72M | 4.00M | 4.13M | 4.89M | 5.27M | 5.82M |
|   of which attendee had no STI (wasted attendance) | 0.13M | 0.11M | 0.23M | 0.35M | 0.58M | 0.68M | 0.93M | 1.05M | 1.21M |
|   PN indices over-treated (no STI at moment of tx) | 7.10M | 0.64M | 0.70M | 0.74M | 0.83M | 1.01M | 1.38M | 1.69M | 2.09M |

## Notes

- **NG fix:** stisim ships `GonorrheaTreatment` with an AMR tracking state `rel_treat` declared `FloatArr(default=1)`, but starsim does not apply the default to `.raw`. Every agent's rel_treat sits at NaN, so `new_treat_eff = NaN * base_treat_eff = NaN` and the `treat_eff` bernoulli always rejects — 0% NG cures. Worked around locally by treating NaN as the documented default (1.0) in `GonorrheaTreatmentFixed.set_treat_eff`. Calibration baseline (with the bug) treated NG as effectively no-treatment, so NG prevalence in those calibrated draws is an over-estimate; the bug-fixed dynamics drive NG down across all arms.
- **`prop_treated` (event-ratio, lax)** can exceed 100% in the regime where the same agent gets infected and successfully treated more than once over 2027-2040. It is best read as a treatment-volume-per-infection ratio, not a literal patient coverage rate. Reported alongside `prop_cured_3mo` (per-episode, strict) which counts per-episode "newly infected at T0 and successfully treated within 3 months of T0" — implemented via the `CareTimingAnalyzer` in analyzers.py.
- **PN false-alarm index** is computed inside `PartnerNotificationNoCycle.step` by reading `tx.outcomes` across NG/CT/TV/syph treatments: an index UID is "false alarm" if it appears in `outcomes[d].unnecessary` for at least one STI AND does NOT appear in `outcomes[d].(successful|unsuccessful)` for any STI. BV is excluded — BV-only over-treatment that gets correctly caught by metronidazole still triggers PN, and that PN is false-alarm.
- **PN cascade**: still tracks anyone-treated-this-step as index pool, not stratified by which STI triggered treatment. Splitting PN by disease (which STI drove the index case) and by sex (M vs F index / attendee) requires bookkeeping inside `POCPN.notify_attendees` — TODO.
- **FetalHealth wiring** still off. Native syph module gives `new_congenital`; NND + stillborn require FetalHealth + `sti_fetal` connector. Numbers above let us decide whether to enable.