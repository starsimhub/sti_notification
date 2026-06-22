# CLAUDE.md

Health-impact analysis of demand-generation strategies — partner notification (PN) and outreach-driven care-seeking — for STI **undertreatment** in sub-Saharan Africa. Built on STIsim. Companion to `syph_dx_zim` (overtreatment).

See `README.md` for project structure, `ANALYSIS_PLAN.md` for scope, and the per-experiment `SUMMARY.md` files under `experiments/` for results.

## Repo layout (restructured 2026-06-22)

Only **calibration** runs live under `experiments/`, each in its own dated,
sequential folder (`01_2026-06-15_…`, `02_2026-06-22_…`), with that
calibration's figures in the folder. **Scenarios** run through the single root
`run_scenarios.py` (factors in `scenarios.py`); scenario figures go in root
`figures/`, outputs in root `results/` (gitignored). Superseded exploratory
work (PN/condom ladders, wiring + story runs) is under `archive/`.

## State of play

**Active calibration baseline.** `experiments/02_2026-06-22_calibration_per_disease_sustain/` — **26-draw robust ensemble** on **stisim rc1.5.7** with 17 priors, using a **per-disease sustainability filter** (HIV/syph/NG/CT/TV all required to sustain through 2030–2040; the earlier syph-only filter let through ~43% of draws with NG or TV at near-extinction beta values, including the draw 773 that extinguished both in scenarios). Draws live at `experiments/02_2026-06-22_calibration_per_disease_sustain/outputs/draws_used.csv`. Full report in that folder's `SUMMARY.md`. **Predates the BV-in-VDS edit (`SimpleBV` + `bv_care`); re-fire before the headline factorial.**

**Historical baselines.**
- `experiments/01_2026-06-15_calibration_rc1.5.7/` — 53-draw ensemble on the same model but with a syph-only sustainability filter. Superseded because 23/53 draws had NG or TV `beta_m2f` < 0.05, near the extinction threshold.
- 169-draw ensemble on `main` under `calibration/artifacts/` against an older stisim base. The 41-experiment development history is on the `archive/calibration-2026-06` tag.

**Active work.** POC scenario factorial on the `scenarios/zimbabwe` branch, driven by root `run_scenarios.py`: `SOC` + `POC × CARE_SEEKING × PN_INTENSITY × BUNDLED_PREVENTION` (5×5×5 = 125, + SOC = 126 cells), propagated through the 26-draw ensemble, reporting the endpoints in `ANALYSIS_PLAN.md`. `SMOKE=1` runs a 6-cell wiring check.

## Intake

**Model.** STIsim rc1.5.7 / Starsim 3.3.2 simulation of HIV + syph + GUD-placeholder + NG/CT/TV/BV in Zimbabwe (`model.py`). The `custom=` slot wires `FetalHealth` + `sti_fetal` connector for adverse pregnancy / birth outcomes. Single-sim runtime at the calibrated configuration (10k agents, 1985–2040): ~90–120 s.

`pn.py` provides this project's edge-stratified `PartnerNotification` class and `pn_rates` helper, used as the parent of `SyndromicPN` and `POCPN` in `interventions.py`. See its docstring for the rate-spec shapes accepted by `pn_rates`.

**Question.** Health-impact analysis: how do PN coverage and care-seeking intensity change APO/ABO/DALY outcomes, HIV infections, and onward syph transmission, and does better diagnostic accuracy reduce unnecessary partner notification? The posterior ensemble (not a point fit) feeds the analysis.

**Data.** NG/CT/TV prevalence from `data/zimbabwe_sti_data.csv`. HIV from `data/zimbabwe_hiv_calib.csv`. Syph from `data/zimbabwe_syph_data.csv`. ZIMPHIA 2015–16 age × sex syph table in `data/zimphia_2015_syph_table_18_4_A.md`.

**Constraints.** IDM Azure VM, 120 cores. ~July 2026 deadline for full deliverable. Solo (Robyn).

### Calibration approach (record)

17 parameters opened up (see `priors.py` and `experiments/01_2026-06-15_calibration_rc1.5.7/SUMMARY.md`): five disease betas (HIV, syph, NG, CT, TV), HIV `rel_init_prev`, HIV–syph coupling, network structure, syphilis natural history. Condom effectiveness, `p_symp`, `p_symp_care=0.75`, and care-seeking rates fixed throughout.

Method: LHS over the prior, single-seed filter on sustained + n_pass ≥ 5, 3-seed robustness re-run, ensemble selection on sustained 3/3 + mean n_pass ≥ 4. Institutional pipeline at `calibration/artifacts/scripts/run_ensemble.py`; experiment driver at `experiments/01_2026-06-15_calibration_rc1.5.7/run.py`. History matching was used early but the syphilis bimodality defeated Bayes-linear emulation — see `calibration/methodology.md` §"Method evolution".

**Calibration findings to carry into scenarios.** HIV calibrates cleanly (ensemble median 11.4% whole-pop, in the UNAIDS band). The syph absolute prev structural ceiling means trep/nontrep medians sit at ~26%/13% vs ZIMPHIA 2.7%/0.8% — documented as a model property, not an artifact. Manuscript framing: HIV is the headline; syph results are *relative-effect contrasts*, not absolute calibration.

### Environment

- Conda env: `starsim` (per global CLAUDE.md; `uv` not installed and not requested).
- stisim pinned to rc1.5.7.
