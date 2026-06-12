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
  - **NG point-prevalence at 2040:** 0.7% (A) → 1.0% (C3) → 0.9% (D) → 0.5% (E2). E2 vs A: -26% relative.
  - **CT point-prevalence at 2040:** 9.8% (A) → 9.5% (C3) → 8.9% (D) → 7.6% (E2). E2 vs A: -22% relative.
  - **TV point-prevalence at 2040:** 12.3% (A) → 10.2% (C3) → 9.6% (D) → 8.3% (E2). E2 vs A: -32% relative.
  - **Syph sexually-transmissible prevalence at 2040** (primary + secondary + early latent — WHO early infectious syphilis): 3.7% (A) → 3.3% (B) → 3.7% (C3) → 3.7% (D) → 2.2% (E2) → 1.4% (E3). E3 vs A: -63% relative. The E-arms care-seeking multiplier scales syph symp_test_prob in addition to NG/CT/TV `p_symp_care` — so syph finally responds to demand-gen, in contrast to the earlier flat C3→D→E2 (where E only scaled NG/CT/TV). Total syph prev not reported — the calibration ensemble overshoots total syph prev (latent/tertiary), so the policy-relevant slice is the sexually-transmissible fraction.
  - **Unnecessary syph treatments A→B:** 5.27M → 0.41M (-92%) — POC dx specificity win still clean.
  - **BV prevalence at 2040 (all arms):** ~40.2%. BV is the dominant cause of VDS presentations — most women presenting with VDS-like symptoms in this model have BV, not NG/CT/TV. Under SOC syndromic management they get presumptively treated for NG/CT/TV and become PN indices.
  - **PN false-alarm indices (A):** 7.08M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (B):** 0.64M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (C3):** 0.80M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (D):** 0.97M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **PN false-alarm indices (E2):** 1.62M agents triggered PN despite having NO actual STI at the moment of treatment.
  - **Wasted PN attendance:** 0.11M / 0.91M (12.0%) in A vs 0.81M / 4.45M (18.1%) in E3. Scaling PN volume reaches further into casual partnerships with lower STI co-prev → wasted-fraction creeps up.

Per-episode "treated within N months of acquisition" (`CareTimingAnalyzer`, A vs E3):
  - **NG (A → E3):** 3-mo 22.2% → 27.6% ; 6-mo 23.1% → 30.0%.
  - **CT (A → E3):** 3-mo 9.6% → 42.8% ; 6-mo 12.9% → 50.3%.
  - **TV (A → E3):** 3-mo 4.1% → 22.0% ; 6-mo 4.3% → 23.2%.
  - **SYPH (A → E3):** 3-mo 31.3% → 54.3% ; 6-mo 42.6% → 63.3%.

**Syph APO:** stisim's `new_congenital` ~33-36K cases per arm; `new_nnds` and `new_stillborns` are placeholder fields never written without FetalHealth wiring.

## Per-disease summary, by arm

Mean over draws+seeds. All counts in millions over 2027-2040.
`prop_treated` = `tx_success / new_inf` is the share of new infections that ended up cleared by a treatment. `prev_end` is point-prevalence at sim end (2040).

### SYPH
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 3.46M | 2.99M | 3.15M | 3.20M | 3.42M | 3.36M | 2.17M | 2.65M | 1.58M |
|   new inf — F | 1.76M | 1.56M | 1.66M | 1.69M | 1.82M | 1.77M | 1.08M | 1.27M | 0.70M |
|   new inf — M | 1.70M | 1.42M | 1.49M | 1.52M | 1.59M | 1.60M | 1.09M | 1.39M | 0.89M |
| Treatments — total | 8.17M | 2.67M | 2.89M | 3.04M | 3.34M | 3.30M | 2.61M | 3.28M | 2.70M |
|   successful | 2.65M | 2.20M | 2.39M | 2.51M | 2.76M | 2.72M | 1.85M | 2.32M | 1.42M |
|   unnecessary | 5.27M | 0.41M | 0.43M | 0.46M | 0.50M | 0.50M | 0.70M | 0.88M | 1.23M |
| n_infected (point, 2040) | 1865.3K | 1849.8K | 1821.4K | 1756.1K | 1728.1K | 1715.9K | 1078.2K | 1053.4K | 654.2K |
| Sexually transmissible prev (point, 2040) | 3.7% | 3.3% | 3.5% | 3.4% | 3.7% | 3.7% | 2.1% | 2.2% | 1.4% |
| 3-month treatment rate | 31.3% | 32.1% | 32.5% | 32.8% | 33.2% | 32.9% | 39.1% | 46.9% | 54.3% |
| 6-month treatment rate | 42.6% | 42.8% | 43.4% | 43.8% | 44.3% | 44.1% | 50.5% | 58.3% | 63.3% |

### NG
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 4.85M | 7.62M | 7.54M | 7.42M | 7.28M | 6.56M | 5.04M | 4.48M | 4.22M |
|   new inf — F | 2.26M | 3.46M | 3.45M | 3.40M | 3.35M | 3.15M | 2.36M | 2.10M | 1.98M |
|   new inf — M | 2.59M | 4.16M | 4.10M | 4.02M | 3.93M | 3.41M | 2.69M | 2.37M | 2.24M |
| Treatments — total | 9.90M | 2.09M | 2.16M | 2.21M | 2.29M | 2.31M | 2.36M | 2.40M | 2.48M |
|   successful | 1.13M | 1.42M | 1.45M | 1.47M | 1.50M | 1.44M | 1.33M | 1.26M | 1.23M |
|   unnecessary | 8.73M | 0.61M | 0.64M | 0.68M | 0.72M | 0.81M | 0.98M | 1.09M | 1.19M |
| n_infected (point, 2040) | 105.4K | 163.4K | 159.6K | 154.7K | 147.6K | 134.5K | 96.3K | 78.2K | 76.9K |
| Prevalence (point, 2040) | 0.7% | 1.1% | 1.0% | 1.0% | 1.0% | 0.9% | 0.6% | 0.5% | 0.5% |
| 3-month treatment rate | 22.2% | 17.5% | 17.8% | 18.1% | 18.7% | 20.0% | 23.8% | 25.3% | 27.6% |
| 6-month treatment rate | 23.1% | 18.7% | 19.1% | 19.6% | 20.4% | 22.1% | 26.2% | 27.4% | 30.0% |

### CT
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 14.86M | 19.11M | 18.92M | 18.78M | 18.54M | 18.04M | 17.45M | 17.29M | 17.22M |
|   new inf — F | 8.14M | 8.76M | 8.75M | 8.73M | 8.70M | 8.73M | 8.35M | 8.48M | 8.43M |
|   new inf — M | 6.73M | 10.36M | 10.19M | 10.06M | 9.85M | 9.32M | 9.11M | 8.81M | 8.81M |
| Treatments — total | 9.90M | 7.27M | 7.55M | 7.81M | 8.20M | 8.58M | 9.88M | 10.36M | 10.54M |
|   successful | 5.90M | 6.28M | 6.49M | 6.70M | 7.00M | 7.29M | 8.35M | 8.70M | 8.77M |
|   unnecessary | 3.35M | 0.30M | 0.34M | 0.37M | 0.43M | 0.49M | 0.60M | 0.69M | 0.80M |
| n_infected (point, 2040) | 1544.6K | 1594.8K | 1564.6K | 1533.8K | 1499.8K | 1408.6K | 1252.1K | 1201.2K | 1184.3K |
| Prevalence (point, 2040) | 9.8% | 10.1% | 9.9% | 9.7% | 9.5% | 8.9% | 7.9% | 7.6% | 7.5% |
| 3-month treatment rate | 9.6% | 28.1% | 28.3% | 28.7% | 29.0% | 30.5% | 37.3% | 40.8% | 42.8% |
| 6-month treatment rate | 12.9% | 31.5% | 32.0% | 32.6% | 33.3% | 36.2% | 44.5% | 48.3% | 50.3% |

### TV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 44.22M | 44.92M | 44.48M | 44.08M | 43.40M | 41.89M | 40.81M | 40.02M | 39.22M |
|   new inf — F | 11.60M | 11.75M | 12.16M | 12.50M | 12.95M | 13.38M | 13.33M | 13.37M | 13.37M |
|   new inf — M | 32.65M | 33.19M | 32.35M | 31.60M | 30.47M | 28.53M | 27.50M | 26.67M | 25.87M |
| Treatments — total | 3.51M | 6.21M | 6.50M | 6.76M | 7.13M | 7.28M | 9.06M | 10.62M | 12.24M |
|   successful | 2.04M | 4.93M | 5.17M | 5.38M | 5.67M | 5.74M | 7.21M | 8.52M | 9.99M |
|   unnecessary | 1.24M | 0.73M | 0.76M | 0.79M | 0.84M | 0.90M | 1.05M | 1.16M | 1.15M |
| n_infected (point, 2040) | 1933.2K | 1804.1K | 1744.8K | 1680.8K | 1596.7K | 1500.6K | 1389.3K | 1305.2K | 1197.4K |
| Prevalence (point, 2040) | 12.3% | 11.5% | 11.1% | 10.7% | 10.2% | 9.6% | 8.9% | 8.3% | 7.6% |
| 3-month treatment rate | 4.1% | 9.7% | 9.9% | 10.1% | 10.5% | 11.2% | 14.9% | 18.5% | 22.0% |
| 6-month treatment rate | 4.3% | 10.3% | 10.6% | 10.8% | 11.3% | 12.1% | 16.2% | 19.8% | 23.2% |

### BV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 78.84M | 75.96M | 76.67M | 77.22M | 77.94M | 78.24M | 81.68M | 84.21M | 84.66M |
|   new inf — F | 78.90M | 76.02M | 76.73M | 77.28M | 78.00M | 78.30M | 81.74M | 84.27M | 84.72M |
|   new inf — M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M |
| Treatments — total | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   successful | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   unnecessary | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| n_infected (point, 2040) | 10731.7K | 10771.1K | 10760.8K | 10752.4K | 10743.8K | 10744.7K | 10715.1K | 10696.8K | 10719.9K |
| Prevalence (point, 2040) | 40.2% | 40.4% | 40.3% | 40.2% | 40.2% | 40.2% | 40.0% | 39.9% | 39.9% |
| 3-month treatment rate | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| 6-month treatment rate | NA | NA | NA | NA | NA | NA | NA | NA | NA |

## Syph APO/ABO

Native syph module results, summed over 2027-2040.

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| Congenital syph cases | 35.6K | 38.5K | 36.8K | 37.2K | 36.9K | 38.0K | 23.2K | 23.3K | 12.8K |
| Congenital deaths (=NND+stillborn) | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Neonatal deaths (NND)* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Stillbirths* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |

*\* NND/stillborn rely on `FetalHealth` to fire ti_nnd / ti_stillborn. Without FetalHealth wired (this pilot), those are 0 across all arms.*

## HIV + partner notification

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| HIV new infections | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.51M | 0.50M |
| PN partners notified | 1.40M | 1.41M | 2.02M | 2.59M | 3.68M | 3.75M | 4.23M | 4.44M | 4.76M |
| PN partners attending | 0.91M | 0.91M | 1.68M | 2.38M | 3.45M | 3.50M | 3.95M | 4.12M | 4.45M |
|   of which attendee had no STI (wasted attendance) | 0.11M | 0.09M | 0.19M | 0.28M | 0.43M | 0.52M | 0.67M | 0.73M | 0.81M |
|   PN indices over-treated (no STI at moment of tx) | 7.08M | 0.64M | 0.69M | 0.73M | 0.80M | 0.97M | 1.32M | 1.62M | 2.01M |

## Notes

- **NG fix:** stisim ships `GonorrheaTreatment` with an AMR tracking state `rel_treat` declared `FloatArr(default=1)`, but starsim does not apply the default to `.raw`. Every agent's rel_treat sits at NaN, so `new_treat_eff = NaN * base_treat_eff = NaN` and the `treat_eff` bernoulli always rejects — 0% NG cures. Worked around locally by treating NaN as the documented default (1.0) in `GonorrheaTreatmentFixed.set_treat_eff`. Calibration baseline (with the bug) treated NG as effectively no-treatment, so NG prevalence in those calibrated draws is an over-estimate; the bug-fixed dynamics drive NG down across all arms.
- **`prop_treated` (event-ratio, lax)** can exceed 100% in the regime where the same agent gets infected and successfully treated more than once over 2027-2040. It is best read as a treatment-volume-per-infection ratio, not a literal patient coverage rate. Reported alongside `prop_cured_3mo` (per-episode, strict) which counts per-episode "newly infected at T0 and successfully treated within 3 months of T0" — implemented via the `CareTimingAnalyzer` in analyzers.py.
- **PN false-alarm index** is computed inside `PartnerNotificationNoCycle.step` by reading `tx.outcomes` across NG/CT/TV/syph treatments: an index UID is "false alarm" if it appears in `outcomes[d].unnecessary` for at least one STI AND does NOT appear in `outcomes[d].(successful|unsuccessful)` for any STI. BV is excluded — BV-only over-treatment that gets correctly caught by metronidazole still triggers PN, and that PN is false-alarm.
- **PN cascade**: still tracks anyone-treated-this-step as index pool, not stratified by which STI triggered treatment. Splitting PN by disease (which STI drove the index case) and by sex (M vs F index / attendee) requires bookkeeping inside `POCPN.notify_attendees` — TODO.
- **FetalHealth wiring** still off. Native syph module gives `new_congenital`; NND + stillborn require FetalHealth + `sti_fetal` connector. Numbers above let us decide whether to enable.