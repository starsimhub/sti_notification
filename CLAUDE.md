# CLAUDE.md

Health-impact analysis of demand-generation strategies — partner notification (PN) and outreach-driven care-seeking — for STI **undertreatment** in sub-Saharan Africa. Built on STIsim. Companion to `syph_dx_zim` (overtreatment).

See `README.md` for project structure, `ANALYSIS_PLAN.md` for scope and phasing, and `calibration/README.md` for the calibration record.

## State of play

**Calibration is complete.** A 200-draw posterior ensemble (× 3 seeds = 600 sims) is captured under `calibration/artifacts/`. Full institutional record — methodology, assumptions, recalibration guide — under `calibration/`. The 41-experiment development history is preserved on the `archive/calibration-2026-06` tag (branch `calibration/zimbabwe`); that branch is archival and should not be merged or extended.

**Active work:** PN-intervention scenarios and decision analysis, on a separate branch off main (e.g. `scenarios/zimbabwe`). These propagate the posterior through counterfactual PN coverage / care-seeking settings and report CEAC + EVPI per the `calib:decision-analysis` skill.

## Intake

**Model.** STIsim 1.5.5 / Starsim 3.3.2 simulation of HIV + syph + GUD-placeholder + NG/CT/TV/BV in Zimbabwe (`model.py`). With the `custom=` slot wiring `FetalHealth` + `sti_fetal` connector for adverse pregnancy / birth outcomes. Single-sim runtime at the calibrated configuration (10k agents, 1985–2040): ~90–120 s.

**Question.** Decision analysis: thresholds for PN coverage and care-seeking intensity that yield meaningful APO/ABO/DALY impact, with the diagnostic accuracy → unnecessary partner-notification angle as the secondary contribution. The posterior ensemble (not a point fit) feeds the decision analysis.

**Data.** NG/CT/TV prevalence from `data/zimbabwe_sti_data.csv`. HIV from `data/zimbabwe_hiv_calib.csv`. Syph from `data/zimbabwe_syph_data.csv`. ZIMPHIA 2015–16 age × sex syph table in `data/zimphia_2015_syph_table_18_4_A.md`.

**Constraints.** IDM Azure VM, 120 cores. ~July 2026 deadline for full deliverable. Solo (Robyn).

### Calibration approach (record)

19 parameters opened up (see `priors.py` and `calibration/methodology.md`): five disease betas (HIV, syph, NG, CT, TV), HIV `rel_init_prev`, HIV–syph coupling, network structure, syphilis natural history, marital dynamics. Condom effectiveness, `p_symp`, `p_symp_care=0.75`, and care-seeking rates fixed throughout.

Final method: LHS over the prior, single-seed filter on sustained + n_pass ≥ 5, 3-seed robustness re-run, ensemble selection on sustained 3/3 + mean n_pass ≥ 4. History matching was used early but the syphilis bimodality defeated Bayes-linear emulation — see `calibration/methodology.md` §"Method evolution" for the reversal.

### Environment

- Conda env: `starsim` (per global CLAUDE.md; `uv` not installed and not requested)
- **Upstream stisim dependency**: the calibration requires three STIsim feature branches (`feat/partner-notification-network`, `feat/marital-act-decay`, `feat/syph-detectable-state`) until they merge into stisim main. See `calibration/recalibration_guide.md` §"Software".
