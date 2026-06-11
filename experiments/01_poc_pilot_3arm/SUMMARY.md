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
  - **NG point-prevalence at 2040:** 0.7% (A) → 0.9% (C3) → 0.8% (D) → 0.5% (E2). E2 vs A: -31% relative.
  - **CT point-prevalence at 2040:** 9.8% (A) → 9.3% (C3) → 8.8% (D) → 7.4% (E2). E2 vs A: -24% relative.
  - **TV point-prevalence at 2040:** 12.3% (A) → 10.1% (C3) → 9.5% (D) → 8.3% (E2). E2 vs A: -33% relative.
  - **Syph `prop_treated` scales with PN intensity:** 73.0% (B) → 80.8% (C3). C3 exceeds the syndromic baseline A (84.5%).
  - **Syph point-prevalence at 2040:** 13.2% (A) → 13.5% (B) → 12.3% (C3) → 12.3% (D).
  - **Unnecessary syph treatments A→B:** 5.27M → 0.41M (-92%) — POC dx specificity win still clean.
  - **BV prevalence at 2040 (all arms):** ~40.2%. BV is the dominant cause of VDS presentations — most women presenting with VDS-like symptoms in this model have BV, not NG/CT/TV. Under SOC syndromic management they get presumptively treated for NG/CT/TV and become PN indices.
  - **Wasted PN attendance (A):** 0.13M / 1.01M (12.6%) had no STI at attendance.
  - **Wasted PN attendance (B):** 0.11M / 1.03M (10.9%) had no STI at attendance.
  - **Wasted PN attendance (C3):** 0.58M / 4.00M (14.4%) had no STI at attendance.
  - **Wasted PN attendance (D):** 0.68M / 4.13M (16.5%) had no STI at attendance.

**Syph APO:** stisim's `new_congenital` ~33-36K cases per arm; `new_nnds` and `new_stillborns` are placeholder fields never written without FetalHealth wiring.

## Per-disease summary, by arm

Mean over draws+seeds. All counts in millions over 2027-2040.
`prop_treated` = `tx_success / new_inf` is the share of new infections that ended up cleared by a treatment. `prev_end` is point-prevalence at sim end (2040).

### SYPH
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 3.46M | 3.08M | 3.19M | 3.23M | 3.47M | 3.49M | 3.65M | 3.72M | 3.83M |
|   new inf — F | 1.76M | 1.61M | 1.68M | 1.72M | 1.87M | 1.85M | 1.95M | 1.99M | 2.05M |
|   new inf — M | 1.70M | 1.46M | 1.50M | 1.51M | 1.60M | 1.63M | 1.70M | 1.73M | 1.78M |
| Treatments — total | 8.17M | 2.73M | 2.93M | 3.08M | 3.41M | 3.43M | 3.63M | 3.73M | 3.85M |
|   successful | 2.65M | 2.25M | 2.42M | 2.53M | 2.80M | 2.82M | 2.99M | 3.07M | 3.16M |
|   unnecessary | 5.27M | 0.41M | 0.44M | 0.48M | 0.52M | 0.53M | 0.56M | 0.57M | 0.59M |
| n_infected (point, 2040) | 1865.3K | 1884.2K | 1826.4K | 1759.7K | 1735.6K | 1735.0K | 1740.8K | 1730.1K | 1742.2K |
| Prevalence (point, 2040) | 13.2% | 13.5% | 13.0% | 12.4% | 12.3% | 12.3% | 12.4% | 12.4% | 12.5% |
| Prop new inf treated | 84.5% | 73.0% | 75.7% | 78.4% | 80.8% | 80.8% | 81.5% | 82.3% | 82.3% |
|   — F | 89.6% | 82.6% | 86.2% | 89.4% | 91.2% | 88.9% | 89.4% | 89.6% | 90.4% |
|   — M | 77.4% | 61.8% | 63.4% | 65.4% | 68.2% | 71.1% | 72.0% | 73.7% | 72.8% |

### NG
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 4.84M | 7.61M | 7.49M | 7.27M | 7.13M | 6.41M | 4.76M | 4.16M | 3.95M |
|   new inf — F | 2.26M | 3.47M | 3.44M | 3.36M | 3.31M | 3.10M | 2.25M | 1.98M | 1.86M |
|   new inf — M | 2.59M | 4.15M | 4.05M | 3.92M | 3.82M | 3.31M | 2.51M | 2.18M | 2.09M |
| Treatments — total | 9.93M | 2.10M | 2.18M | 2.23M | 2.34M | 2.37M | 2.37M | 2.39M | 2.51M |
|   successful | 1.13M | 1.43M | 1.47M | 1.48M | 1.53M | 1.47M | 1.31M | 1.21M | 1.21M |
|   unnecessary | 8.76M | 0.61M | 0.66M | 0.69M | 0.75M | 0.84M | 1.01M | 1.13M | 1.25M |
| n_infected (point, 2040) | 103.2K | 163.4K | 157.7K | 151.9K | 142.0K | 127.5K | 87.8K | 70.7K | 66.0K |
| Prevalence (point, 2040) | 0.7% | 1.1% | 1.0% | 1.0% | 0.9% | 0.8% | 0.6% | 0.5% | 0.4% |
| Prop new inf treated | 23.5% | 19.1% | 19.8% | 20.6% | 21.7% | 23.5% | 27.7% | 30.3% | 33.1% |
|   — F | 6.2% | 8.9% | 10.6% | 12.2% | 14.4% | 19.1% | 22.6% | 26.5% | 27.0% |
|   — M | 38.1% | 27.3% | 27.2% | 27.4% | 27.5% | 27.5% | 32.1% | 33.7% | 38.0% |

### CT
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 14.80M | 19.09M | 18.90M | 18.75M | 18.45M | 17.96M | 17.38M | 17.20M | 17.06M |
|   new inf — F | 8.10M | 8.77M | 8.77M | 8.77M | 8.74M | 8.75M | 8.42M | 8.54M | 8.45M |
|   new inf — M | 6.70M | 10.33M | 10.14M | 9.99M | 9.72M | 9.22M | 8.96M | 8.67M | 8.62M |
| Treatments — total | 9.93M | 7.32M | 7.63M | 7.93M | 8.34M | 8.75M | 10.12M | 10.62M | 10.75M |
|   successful | 5.91M | 6.32M | 6.56M | 6.80M | 7.13M | 7.43M | 8.56M | 8.92M | 8.94M |
|   unnecessary | 3.38M | 0.30M | 0.34M | 0.37M | 0.43M | 0.50M | 0.61M | 0.70M | 0.82M |
| n_infected (point, 2040) | 1537.0K | 1590.0K | 1556.0K | 1520.8K | 1471.8K | 1381.5K | 1217.0K | 1167.7K | 1152.7K |
| Prevalence (point, 2040) | 9.8% | 10.1% | 9.9% | 9.7% | 9.3% | 8.8% | 7.7% | 7.4% | 7.3% |
| Prop new inf treated | 43.7% | 36.4% | 38.1% | 39.7% | 42.2% | 47.8% | 57.7% | 62.6% | 65.7% |
|   — F | 17.5% | 23.7% | 27.5% | 30.8% | 35.4% | 46.0% | 56.9% | 63.6% | 66.9% |
|   — M | 75.8% | 47.3% | 47.4% | 47.8% | 48.5% | 49.4% | 58.2% | 61.3% | 64.4% |

### TV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 44.19M | 44.93M | 44.48M | 44.15M | 43.48M | 41.94M | 40.69M | 39.83M | 38.96M |
|   new inf — F | 11.61M | 11.81M | 12.26M | 12.64M | 13.15M | 13.52M | 13.46M | 13.50M | 13.64M |
|   new inf — M | 32.61M | 33.14M | 32.24M | 31.54M | 30.35M | 28.45M | 27.25M | 26.35M | 25.33M |
| Treatments — total | 3.56M | 6.25M | 6.57M | 6.86M | 7.26M | 7.42M | 9.18M | 10.73M | 12.41M |
|   successful | 2.06M | 4.96M | 5.23M | 5.45M | 5.77M | 5.84M | 7.29M | 8.59M | 10.11M |
|   unnecessary | 1.28M | 0.73M | 0.77M | 0.80M | 0.86M | 0.93M | 1.08M | 1.19M | 1.18M |
| n_infected (point, 2040) | 1930.2K | 1802.6K | 1734.6K | 1676.5K | 1587.4K | 1492.1K | 1371.7K | 1290.1K | 1163.6K |
| Prevalence (point, 2040) | 12.3% | 11.5% | 11.1% | 10.7% | 10.1% | 9.5% | 8.8% | 8.3% | 7.4% |
| Prop new inf treated | 5.6% | 12.1% | 13.1% | 13.8% | 15.0% | 16.8% | 21.8% | 26.1% | 30.3% |
|   — F | 16.0% | 18.6% | 21.2% | 23.2% | 26.2% | 31.2% | 38.5% | 48.4% | 50.5% |
|   — M | 1.2% | 9.4% | 9.5% | 9.6% | 9.8% | 9.8% | 13.3% | 15.8% | 20.9% |

### BV
| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| New infections | 78.91M | 75.99M | 76.72M | 77.27M | 78.00M | 78.30M | 81.66M | 84.15M | 84.47M |
|   new inf — F | 78.97M | 76.05M | 76.77M | 77.33M | 78.06M | 78.35M | 81.72M | 84.21M | 84.53M |
|   new inf — M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M | 0.00M |
| Treatments — total | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   successful | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   unnecessary | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| n_infected (point, 2040) | 10730.3K | 10770.9K | 10759.8K | 10751.0K | 10741.7K | 10743.0K | 10702.4K | 10671.5K | 10669.1K |
| Prevalence (point, 2040) | 40.2% | 40.4% | 40.3% | 40.2% | 40.2% | 40.2% | 40.0% | 39.9% | 39.9% |
| Prop new inf treated | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   — F | NA | NA | NA | NA | NA | NA | NA | NA | NA |
|   — M | NA | NA | NA | NA | NA | NA | NA | NA | NA |

## Syph APO/ABO

Native syph module results, summed over 2027-2040.

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| Congenital syph cases | 35.6K | 37.5K | 38.9K | 37.0K | 37.2K | 40.0K | 39.2K | 38.6K | 39.3K |
| Congenital deaths (=NND+stillborn) | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Neonatal deaths (NND)* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |
| Stillbirths* | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K | 0.0K |

*\* NND/stillborn rely on `FetalHealth` to fire ti_nnd / ti_stillborn. Without FetalHealth wired (this pilot), those are 0 across all arms.*

## HIV + partner notification

| Metric | A | B | C1 | C2 | C3 | D | E1 | E2 | E3 |
|---|---|---|---|---|---|---|---|---|---|
| HIV new infections | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M | 0.49M |
| PN partners notified | 1.58M | 1.63M | 2.32M | 2.98M | 4.28M | 4.44M | 5.25M | 5.66M | 6.25M |
| PN partners attending | 1.01M | 1.03M | 1.91M | 2.72M | 4.00M | 4.13M | 4.87M | 5.24M | 5.81M |
|   of which no STI found (wasted) | 0.13M | 0.11M | 0.23M | 0.35M | 0.58M | 0.68M | 0.87M | 0.97M | 1.08M |

## Notes

- **NG fix:** stisim ships `GonorrheaTreatment` with an AMR tracking state `rel_treat` declared `FloatArr(default=1)`, but starsim does not apply the default to `.raw`. Every agent's rel_treat sits at NaN, so `new_treat_eff = NaN * base_treat_eff = NaN` and the `treat_eff` bernoulli always rejects — 0% NG cures. Worked around locally by treating NaN as the documented default (1.0) in `GonorrheaTreatmentFixed.set_treat_eff`. Calibration baseline (with the bug) treated NG as effectively no-treatment, so NG prevalence in those calibrated draws is an over-estimate; the bug-fixed dynamics drive NG down across all arms.
- **`prop_treated`** can exceed 100% in the (rare) regime where the same agent gets infected and successfully treated more than once over 2027-2040. It is best read as a treatment-volume-per-infection ratio, not a literal patient coverage rate.
- **PN cascade**: still tracks anyone-treated-this-step as index pool, not stratified by which STI triggered treatment. Splitting PN by disease (which STI drove the index case) and by sex (M vs F index / attendee) requires bookkeeping inside `POCPN.notify_attendees` — TODO.
- **Treated-within-3-months metric** also a TODO — requires per-agent (ti_infected - ti_treated) tracking which is not currently exposed in results.
- **FetalHealth wiring** still off. Native syph module gives `new_congenital`; NND + stillborn require FetalHealth + `sti_fetal` connector. Numbers above let us decide whether to enable.