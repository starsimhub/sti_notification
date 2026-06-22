# Exp 08 — PN x bundled-prevention scenario run (ensemble)

**Question.** Across the sustained calibration ensemble, how do partner-
notification intensity and bundled prevention (condoms + counselling for the
diagnosed) change STI burden, relative to syndromic standard of care? This is
the headline scenario run feeding the slides and dashboard.

## What it runs

10 cells x N_DRAWS x N_SEEDS. Each cell = one (dx, PN intensity, bundled
prevention) combination, layered on a calibrated draw. Ladders are defined in
`scenarios.py` (repo root).

| cell | dx | PN intensity | bundled prevention |
|---|---|---|---|
| SOC | syndromic | baseline | none |
| POC_pn_baseline | POC | baseline | none  (= POC reference) |
| POC_pn_low / moderate / high / maximum | POC | ladder | none |
| POC_bp_low / moderate / high / maximum | POC | baseline | coverage ladder |

PN intensity is a single axis co-varying notify + attend; bundled prevention
is a single axis on coverage of the diagnosed (a `rel_sus` reduction for a
window, via `experiments/06_condom_ladder/cond.py:CondomCounseling`).

## How to run

From the repo root, in the `starsim` conda env, on a multi-core machine:

```bash
conda run -n starsim env N_SEEDS=1 N_WORKERS=60 \
    python experiments/08_pn_bp_scenarios/run.py
```

- `N_SEEDS=1` is the agreed first run (10 cells x 26 draws x 1 seed = 260 sims).
- `N_WORKERS` = cores to use (60 on the VM).
- `DRAWS=/path/to/draws_used.csv` overrides the ensemble path (see prerequisite).

Expected wall time on 60 cores: about 10 to 12 min at 1 seed (measured per-sim
~105 s for one 10k-agent 1985-2040 sim with FetalHealth, parallelised over
260 sims).

## Prerequisite (important)

`DRAWS_CSV` must point at the ACTIVE calibration baseline, which must:
1. have NG/CT/TV/syphilis all sustaining (per-disease sustainability filter), and
2. have been calibrated with the **BV-in-VDS** model (`SimpleBV` + `bv_care` in
   `seeking_care_vds`).

The current default path
(`experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv`,
26 draws) satisfies (1) but **predates the BV edit**, so re-fire calibration
first, then either replace that file or pass `DRAWS=` to the re-fired ensemble.

## Outputs

`outputs/results.jsonl`, one JSON row per (cell, draw, seed) with: per-disease
new infections and end prevalence (hiv/ng/ct/tv/syph), treatments
(total/success/unnecessary), PN notified/attending, FetalHealth APO/ABO
(n_lbw/sga/svn/births), and syph new_congenital. All summed over 2027-2040.

## Caveat

PN intensity and bundled prevention are applied for the whole sim; the POC
switch happens at intv_year (2027); endpoints are summed over 2027-2040
(matches exps 05-07). A strict from-2027 counterfactual would gate PN
intensity at 2027 too; deferred.
