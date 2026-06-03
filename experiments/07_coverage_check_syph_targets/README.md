# Exp 07 — Coverage check: corrected syphilis targets

**Question.** Does the prior predictive ensemble cover the corrected
syphilis calibration targets? Exp 06 passed coverage against a single
mismatched target (`syph.prevalence` plotted against BMJ
`active_prevalence`). This experiment re-checks coverage with seven
properly defined syphilis indicators from ZIMPHIA and BMJ:

- Current infection prevalence by sex (ZIMPHIA: 1% F, 0.6% M)
- Seroprevalence by sex (ZIMPHIA: 3% F, 2.4% M)
- ANC prevalence (BMJ model estimates: ~2%)
- Symptomatic prevalence (primary + secondary; no data target)
- HIV-syphilis coinfection stratification (ZIMPHIA: 2.9% HIV+, 0.4% HIV-)

**Changes from exp 06.**
- `syphilis.py`: added `serological_prevalence` result; fixed by-sex
  `prevalence` denominator to use sexually active adults.
- `model.py`: added `coinfection_stats('syph', 'hiv')` analyzer.
- `zimbabwe_syph_data.csv`: restructured with ZIMPHIA data points and
  correct column names; BMJ estimates retained as ANC prevalence.
- `run.py` / `plot.py`: expanded to extract and plot all new targets.

**Plan.** 100 prior draws, 1 replicate each, 10k agents, 1985–2025.
Same priors as exp 06. Run locally if feasible, otherwise on the VM.

**Success criteria.** For each syphilis target, at least some draws
bracket the observed data. A systematic miss on any target indicates
the prior or model cannot reach that indicator and must be fixed
before calibration. NG/CT/TV/HIV targets are unchanged from exp 06
and expected to pass again.
