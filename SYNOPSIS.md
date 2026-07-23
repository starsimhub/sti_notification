# sti_notification — synopsis

Health-impact analysis of demand-generation and prevention strategies for curable STIs in Zimbabwe. Companion to the [`syph_dx_zim`](https://github.com/starsimhub/syph_dx_zim) overtreatment analysis and the [`stisim_vddx_zim`](https://github.com/starsimhub/stisim_vddx_zim) VDS diagnostic-accuracy analysis. Built on [STIsim](https://github.com/starsimhub/stisim).

## Question

Do partner-notification (PN) reach, symptomatic care-seeking, and bundled prevention (condoms + counseling for the diagnosed) meaningfully compose with a point-of-care (POC) NG/CT/TV diagnostic to reduce the residual undertreatment gap that improved diagnostics alone cannot close? And does the POC step reduce the burden of *unnecessary* partner notification and its associated psychological, safety, and antimicrobial-stewardship harms, alongside unnecessary treatment?

## What we did

Using STIsim, an agent-based microsimulator of co-transmitting HIV, syphilis, NG, CT, TV, and BV calibrated to Zimbabwe (ZIMPHIA + UNAIDS), we ran a 4 × 4 × 4 factorial of three POC-arm levers (care-seeking × partner notification × bundled prevention) plus one syndromic standard-of-care (SOC) baseline cell, for 65 scenario cells total. Each cell was propagated through 5 posterior draws from the exp 06 calibration ensemble with K=5 sim-averaging seeds (1625 sims per run) over 2027–2040. Endpoints per disease (syph, NG, CT, TV): incidence, prevalence, overtreatment, undertreatment, partner-notification volume, and the rate of *unnecessary* partner notification (index cases whose own treatment was in fact a false alarm across NG, CT, and syphilis).

## Headline findings

1. **POC alone** (baseline care-seeking and PN, no bundled prevention) reduces cumulative new curable-STI infections by ~10–15% relative to SOC.
2. **Layering demand-side levers on top** approximately halves cumulative infections at the highest-intensity combination (~50–60% reduction). Care-seeking is the dominant lever for NG, CT, and TV; partner notification is the dominant lever for syphilis.
3. **Overtreatment** (unnecessary NG/CT/TV/syphilis treatments) drops by 75–85% across the factorial, largely invariant to demand-side intensity, a diagnostic-step co-benefit.
4. **Unnecessary partner notification** drops by ~30%, also invariant to PN reach. This ~30% figure is a diagnostic-specificity floor at 95% per-pathogen specificity under Zimbabwe's low true STI prevalence, not a demand-side lever.

## Deliverables

| Artefact | Location |
|---|---|
| Manuscript draft (abstract, methods, 8 results sections, discussion) | [`docs/sti_manuscript.md`](docs/sti_manuscript.md) |
| Deck slide PNGs (slides 3–14) | [`figures/`](figures/) |
| Interactive dashboard (Quarto site) | [`dashboard/`](dashboard/) |
| Aggregated results (committable) | [`results/`](results/) |
| Calibration ensemble | [`experiments/06_2026-06-24_kseed_calibration/`](experiments/06_2026-06-24_kseed_calibration/) |

## Scenario design (as run)

| Lever | Baseline | Low | Moderate | High |
|---|---:|---:|---:|---:|
| Care-seeking multiplier on `p_symp_care` | 1.0 | 1.25 | 1.5 | 1.8 |
| PN notify current, stable / casual | 20% / 10% | 35% / 25% | 55% / 45% | 75% / 65% |
| PN attend female, stable / casual | 80% / 50% | 85% / 60% | 90% / 70% | 92% / 80% |
| PN attend male, stable / casual | 50% / 25% | 60% / 40% | 70% / 55% | 80% / 70% |
| Bundled-prevention coverage of newly-treated | 0% | 25% | 50% | 75% |

Diagnostic-accuracy arm is the framing dimension (SOC syndromic vs POC etiological panel), selected by the `poc=` flag in `make_testing` in [`interventions.py`](interventions.py). Ladders defined in [`scenarios.py`](scenarios.py).

## Reproduction

See [`README.md`](README.md) for the three-stage regeneration pipeline: factorial simulation on VM (`run_scenarios.py`, ~4 h at N_DRAWS=10) then cross-draw aggregation (`process_results.py`, ~5 s) then figures + dashboard.

## Recalibration triggers

Recalibrate if any of:

- Any change to `model.py` that affects calibrated endpoints (new disease, new connector, changed natural-history defaults).
- A stisim minor version bump (1.6.x); parameter scales are not transferable across minor versions per `calibration/recalibration_guide.md`.
- Refreshed ZIMPHIA or UNAIDS data that shifts target bands beyond the 80% CI.

See [`CLAUDE.md`](CLAUDE.md) for the calibration lineage (exps 01–06) and the full history of methodological iterations behind the active baseline.
