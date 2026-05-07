# CLAUDE.md

Health-impact analysis of demand-generation strategies — partner notification (PN) and outreach-driven care-seeking — for STI **undertreatment** in sub-Saharan Africa. Built on STIsim. Companion to `syph_dx_zim` (overtreatment).

See `README.md` for project structure, `ANALYSIS_PLAN.md` for scope and phasing, and `experiments/*/README.md` for per-experiment context.

## Intake

**Model.** STIsim 1.5.5 / Starsim 3.3.2 simulation of HIV + syph + GUD-placeholder + NG/CT/TV/BV in Zimbabwe (`model.py`). With the `custom=` slot wiring `FetalHealth` + `sti_fetal` connector for adverse pregnancy / birth outcomes. Single-sim runtime: ~2–3 s at 1500 agents over 1985–2005 (smoke); ~15–20 s estimated at 5–10 k agents over 1985–2025 (production).

**Question.** Decision analysis: thresholds for PN coverage and care-seeking intensity that yield meaningful APO/ABO/DALY impact, with the diagnostic accuracy → unnecessary partner-notification angle as the secondary contribution. Needs a posterior, not a point fit.

**Data.** NG/CT/TV prevalence from `data/zimbabwe_sti_data.csv` (yearly 2000–2040; weighted in prior fits as ng=2 / ct-women-25-30=2 / tv=1). HIV from `data/zimbabwe_hiv_calib.csv`. Syph from `data/zimbabwe_syph_data.csv`. Joint recalibration on STIsim 1.5.5 (prior fits used 1.4 / 1.5.2 — values not transferable).

**Constraints.** IDM Azure VM, 120 cores / 75–100 in use. ~July 2026 deadline for full deliverable. Solo (Robyn).

### Calibration approach

Eight parameters opened up (`priors.py`): five disease betas (HIV, syph, NG, CT, TV), HIV `rel_init_prev`, two network parameters (`prop_f0`, `m1_conc`). Condom effectiveness, `p_symp`, `p_symp_care=0.75`, and care-seeking rates are *fixed*.

Method preference: history matching + trajectory selection (decision-analysis aim, ~8 parameters, ~15s/sim → HM is the IDM-preferred profile). Formal method choice deferred to the `method-selection` skill after the coverage check (`experiments/01_coverage_check/`).

### Branch + environment

- Working branch: `calibration/zimbabwe`
- Conda env: `starsim` (per global CLAUDE.md; `uv` not installed and not requested)
- **Upstream stisim dependency**: the `SyndromicPN` class in `interventions.py` requires the new `PartnerNotification` API from stisim PR #457 (`feat/partner-notification-network`). On a VM, ensure that branch is checked out for an editable install of stisim until the PR merges to main.
