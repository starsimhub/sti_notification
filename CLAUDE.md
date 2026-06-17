# CLAUDE.md

Health-impact analysis of demand-generation strategies — partner notification (PN) and outreach-driven care-seeking — for STI **undertreatment** in sub-Saharan Africa. Built on STIsim. Companion to `syph_dx_zim` (overtreatment).

See `README.md` for project structure, `ANALYSIS_PLAN.md` for scope, and the per-experiment `SUMMARY.md` files under `experiments/` for results.

## State of play

**Active calibration baseline.** Exp 03 (`experiments/03_calibration_rc1.5.7/`) — 53-draw robust ensemble on **stisim rc1.5.7**, with the marital-act-decay knobs dropped from the prior (17 priors total). Draws used live at `experiments/03_calibration_rc1.5.7/outputs/draws_used.csv`; time-series + age × sex snapshot quantile parquets alongside. Full report in `experiments/03_calibration_rc1.5.7/SUMMARY.md`.

**Historical baseline.** A 169-draw ensemble on `main` against an older stisim base (1.5.5 + three feature branches) lives under `calibration/artifacts/`. Kept as historical comparison; not used for current scenarios. The 41-experiment development history is on the `archive/calibration-2026-06` tag.

**Active work.** PN-intervention scenarios and decision analysis on the `scenarios/zimbabwe` branch. Scenarios run via `run_sweeps.py`. These propagate the 53-draw exp 03 ensemble through counterfactual PN coverage / care-seeking / diagnostic-accuracy settings and report CEAC + EVPI per the `calib:decision-analysis` skill.

## Intake

**Model.** STIsim rc1.5.7 / Starsim 3.3.2 simulation of HIV + syph + GUD-placeholder + NG/CT/TV/BV in Zimbabwe (`model.py`). The `custom=` slot wires `FetalHealth` + `sti_fetal` connector for adverse pregnancy / birth outcomes. Single-sim runtime at the calibrated configuration (10k agents, 1985–2040): ~90–120 s.

**Local STIsim shim.** `pn.py` is a local copy of the edge-stratified `PartnerNotification` class + `pn_rates` helper from upstream stisim PR 505, which did not land in 1.5.7. `SyndromicPN` and `POCPN` re-parent on this local class. Drop `pn.py` and re-parent on `sti.PartnerNotification` once PR 505 merges in a future stisim release.

**Question.** Decision analysis: thresholds for PN coverage and care-seeking intensity that yield meaningful APO/ABO/DALY impact, with the diagnostic accuracy → unnecessary partner-notification angle as the secondary contribution. The posterior ensemble (not a point fit) feeds the decision analysis.

**Data.** NG/CT/TV prevalence from `data/zimbabwe_sti_data.csv`. HIV from `data/zimbabwe_hiv_calib.csv`. Syph from `data/zimbabwe_syph_data.csv`. ZIMPHIA 2015–16 age × sex syph table in `data/zimphia_2015_syph_table_18_4_A.md`.

**Constraints.** IDM Azure VM, 120 cores. ~July 2026 deadline for full deliverable. Solo (Robyn).

### Calibration approach (record)

17 parameters opened up (see `priors.py` and `experiments/03_calibration_rc1.5.7/SUMMARY.md`): five disease betas (HIV, syph, NG, CT, TV), HIV `rel_init_prev`, HIV–syph coupling, network structure, syphilis natural history. The two marital-act-decay parameters (`stable_act_decay`, `client_marital_act_mult`) were opened in exp 40 on the older stisim base but dropped in exp 41 because stisim PR 506 did not land in rc1.5.7; the syph absolute-prev structural ceiling persisted without them, confirming those knobs weren't carrying the ceiling. Condom effectiveness, `p_symp`, `p_symp_care=0.75`, and care-seeking rates fixed throughout.

Method: LHS over the prior, single-seed filter on sustained + n_pass ≥ 5, 3-seed robustness re-run, ensemble selection on sustained 3/3 + mean n_pass ≥ 4. Institutional pipeline at `calibration/artifacts/scripts/run_ensemble.py`; experiment driver at `experiments/03_calibration_rc1.5.7/run.py`. History matching was used early but the syphilis bimodality defeated Bayes-linear emulation — see `calibration/methodology.md` §"Method evolution".

**Calibration findings to carry into scenarios.** HIV calibrates cleanly (ensemble median 11.4% whole-pop, in the UNAIDS band). The syph absolute prev structural ceiling means trep/nontrep medians sit at ~26%/13% vs ZIMPHIA 2.7%/0.8% — documented as a model property, not an artifact. Manuscript framing: HIV is the headline; syph results are *relative-effect contrasts*, not absolute calibration.

### Environment

- Conda env: `starsim` (per global CLAUDE.md; `uv` not installed and not requested).
- **stisim pinned to rc1.5.7.** No local stisim fork; `pn.py` is the only intentional carve-out.
