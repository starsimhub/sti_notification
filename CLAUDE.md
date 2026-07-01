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

**Active calibration baseline.** `experiments/06_2026-06-24_kseed_calibration/` — **500-draw LHS × K=5 sim-averaging** single-phase calibration with continuous weighted goodness-of-fit (replaces exp 04's two-phase LHS + binary per-disease sustainability filter). Same 17 priors as exp 04, same stisim `fix/ng-tx` base (off rc1.5.8, commit `731bc1d`). 311/500 draws (62%) all-five-diseases sustaining; top-30 by GoF used as the ensemble. Default `DRAWS_CSV` in `run_scenarios.py`: `experiments/06_2026-06-24_kseed_calibration/outputs/draws_used.csv`. Full report in that folder's `SUMMARY.md`. NG prev now brackets the empirical band cleanly (top-30 fixed exp 04's "tilts hot" caveat); syph absolute structural ceiling persists.

**Historical baselines.**
- `experiments/05_2026-06-24_kseed_pilot/` — K=5 sim-averaging pilot that validated the single-phase framework against exp 04; small-N predecessor to exp 06.
- `experiments/04_2026-06-23_ng_higher_beta_post_treatfix/` — 27-draw robust ensemble on stisim `fix/ng-tx`, NG `beta_m2f` ∈ [0.10, 0.60], two-phase LHS + sustainability filter. Superseded by exp 06's K=5 + continuous-GoF approach; kept for reference.
- `experiments/03_2026-06-22_calibration_bv_in_vds/` — 26-draw ensemble on stisim rc1.5.7. Sustained NG only via the rel_treat NaN bug. Superseded.
- `experiments/02_2026-06-22_calibration_per_disease_sustain/` — pre-BV-in-VDS ensemble. Superseded.
- `experiments/01_2026-06-15_calibration_rc1.5.7/` — 53-draw ensemble with syph-only sustainability filter. Superseded.
- 169-draw ensemble on `main` under `calibration/artifacts/` against an older stisim base. The 41-experiment development history is on the `archive/calibration-2026-06` tag.

**Active work.** POC scenario factorial driven by root `run_scenarios.py`: `SOC` + `POC × CARE_SEEKING × PN_INTENSITY × BUNDLED_PREVENTION` (4×4×4 = 64 + SOC = **65 cells**, after collapsing ladders to baseline/low/moderate/high — exp 04 had 5×5×5 = 125 cells). Paired K=5 seeds (`seed = draw_idx*1000 + sub_idx`) match the exp 06 calibration so SOC reproduces the calibration's K=5 mean exactly. **Scenarios branch (`scenarios/zimbabwe`) merged to `main` as PR #7 on 2026-06-26.** First full run landed 2026-06-26: 65 cells × 5 draws × K=5 = 1625 sims (~2.5h on 80 workers). Outputs in `results/`; figures in `figures/`.

## VM-only data files (note for the local agent)

The full-run outputs in `results/` are large and not all committed to the repo. When working locally (Mac), be aware:

- `results/scenarios.kavg.csv` (~340 KB) — **IS committed**. K=5-averaged scalar table, 65 cells × 5 draws = 325 rows. Source for any deck plot that only needs cumulative or endpoint metrics (`plotting/plot_slide{3,5,12,13}.py`; the endpoint-bar insets in slides 6/9/10/11; the exploratory `plot_validation*.py` bars).
- `results/scenarios_timeseries.parquet` (~1.7 MB) — **NOT committed**, lives on the IDM Azure VM. Per-(cell, draw, year, disease, result_name) K-averaged TS. Source for the deck time-series panels: `plotting/plot_slide{6,9,10,11}.py`. Also `exploratory/plot_layering*.py`, `plot_epi.py`, `plot_validation.py`.
- `results/scenarios_snapshots.parquet` (~880 KB) — **NOT committed**, VM only. Per-(cell, draw, year, age, sex, disease) K-averaged age × sex snapshots. Source for the age × sex panels in `exploratory/plot_epi.py`.
- `results/scenarios.jsonl` (~5.7 MB) — **NOT committed**, VM only. Per-sim raw scalars (regenerable from `run_scenarios.py`).
- `results/specificity.csv`, `results/soc_overtreatment.csv` — **IS committed**. Person-level SOC vs POC treatment/PN over-rates + (n_drugs, n_actual_STIs) contingency for VDS presenters. Produced by `diagnostics/specificity_tracer.py`. Feed slides 3 + 5.

If a deck plot needs a parquet that isn't there locally, either `scp` it from the VM or rerun `run_scenarios.py` on the VM. The kavg CSV is enough for scalar/bar-only plots.

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
