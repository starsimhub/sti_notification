# Exp 03 — calibration on stisim rc1.5.7

**Question.** Does the rc1.5.7-adapted model (17 priors, dropping
`stable_act_decay` and `client_marital_act_mult`) still produce a
usable ensemble — a moderate set of draws that don't extinguish any
of the seven STIs and bracket the calibration targets — without the
two marital-act-decay knobs that the prior 169-draw baseline
([project_calibration_baseline_2026_06_10](../../../.claude/projects/-home-robyn-sti-notification/memory/project_calibration_baseline_2026_06_10.md))
relied on?

The two dropped priors entered the prior in exp 40 specifically to
close part of the syph leakage gap (`stable_act_decay` decayed
stable-edge coital frequency; `client_marital_act_mult` modeled
client→wife act displacement). Without them, the syph structural
ceiling probably reasserts itself somewhat — the question is whether
the rest of the ensemble (HIV, NG/CT/TV, BV) still calibrates
acceptably, and how the syph contrast moves.

**Plan.** Reuse the existing LHS pipeline at
[calibration/artifacts/scripts/run_ensemble.py](../../calibration/artifacts/scripts/run_ensemble.py),
sized down so wall time is ~2h total:

1. **LHS sweep** — 1000 draws over the 17-parameter prior in
   `priors.py`, run at one seed (`--seed 45`). Per-sim summary stats
   (sustained / n_pass / target band coverage) written to
   `outputs/phase1_results.jsonl`. Expected wall time ≈45 min on 60
   workers.
2. **Multi-seed re-run** on candidates passing the single-seed filter
   (sustained AND n_pass ≥ 5), at 3 seeds each, targeting an ensemble
   of ~100 draws. Per-sim summaries to `outputs/phase2_results.jsonl`.
   Expected wall time ≈25 min.
3. **Selection + summaries** — apply the sustained 3/3 + mean n_pass
   ≥ 4 acceptance criterion, write `outputs/draws_used.csv` and
   `outputs/ensemble_ts_quantiles.parquet`.
4. **Figures** — light set in `figures/`: target-band coverage per
   disease, sustainability summary, comparison to the 2026-06-10
   baseline on the headline endpoints (HIV whole-pop prev, syph
   trep/nontrep, NG/CT/TV/BV prev).

The 2026-06-10 baseline calibration on `main` stays as the historical
comparison; we don't try to reproduce it. This is a fresh prior with
a tagged-release stisim base.

**Success criteria.** A *usable ensemble* (per
[project_calibration_goal_ensemble](../../../.claude/projects/-home-robyn-sti-notification/memory/project_calibration_goal_ensemble.md)):
- **Size:** ~50–100 draws after the 3-seed acceptance filter.
- **Sustainability:** every accepted draw sustains all seven STIs
  through projection window end (no late extinctions).
- **Coverage:** ensemble quantile envelopes bracket the headline
  calibration targets (HIV whole-pop prev 2010–2020, ZIMPHIA syph
  trep/nontrep at 15–64, NG/CT/TV prevalence ranges from
  `data/zimbabwe_sti_data.csv`).

Failure modes worth distinguishing:
- **Insufficient draws (<30 accepted):** prior probably needs widening
  on the dropped-knob-adjacent params (likely network or syph beta)
  before the next attempt.
- **Sustainability fails for syph:** the structural ceiling from the
  baseline calibration was robust; if it now collapses on rc1.5.7,
  that's a model-behavior difference worth understanding before
  scenarios run.
- **Coverage misses headline targets:** which target? HIV miss is
  serious; syph absolute miss is expected and documented; NG/CT/TV
  miss is recalibration-fixable.

Either way, the SUMMARY records what was found. We'll almost
certainly need to redo this — the goal here is a fast first pass on
the rc1.5.7 base, not a final ensemble.
