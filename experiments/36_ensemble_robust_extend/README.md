# Exp 36 — Robust ensemble extension

**Question.** Exp 35 revealed single-seed selection bias: only 39/175
Phase-1 candidates were robustly sustained across 3 seeds. To reach
the 100-draw robust ensemble target, extend the 3-seed evaluation to
the **370 sustained-in-Phase-1 draws that weren't selected for
Phase 2** (because their Phase-1 n_pass was 1-4).

By covering all 545 sustained-in-Phase-1 draws with 3-seed data, we
get an unbiased view of which parameter sets are robustly sustained.
Expected ~120 robust draws (22% rate from exp 35 Phase 2).

**Plan.**

1. Read exp 35's Phase 1 results (`outputs/phase1_results.jsonl`).
2. Identify the 545 draws sustained in Phase 1's single seed.
3. Identify the 175 already in exp 35's Phase 2 (with full 3-seed data).
4. Run the missing 370 draws × 3 seeds = **1110 sims**, ~50 min wall.
5. Combine all 3-seed data from exp 35 Phase 2 + exp 36 = 545 candidate
   draws × 3 seeds = 1635 sim records.
6. Filter to: **sustained 3/3 AND mean n_pass ≥ 5**.
7. Expected ~100-150 robust draws. This is the working ensemble.

**Why not rerun all 1500 Phase-1 draws.** A draw that decayed in
Phase 1's single seed is, by definition, near the decay basin. Even if
seeds 2 or 3 happen to sustain, the draw is operationally fragile —
exactly what we want to exclude. The 545 sustained-in-Phase-1 set is
the right candidate pool.

**Seed scheme.** Phase 2 from exp 35 used `seed = 100_000 + draw_idx
× 10 + s_idx` for s_idx ∈ {0, 1, 2}. Exp 36 uses the same scheme so
3-seed data composes cleanly across the two experiments.

**Outputs.**

- `outputs/extension_results.jsonl` — per-(draw, seed) for the 370
  extra draws (1110 rows)
- `outputs/combined_3seed.csv` — full 3-seed data across all 545
  sustained-in-Phase-1 draws
- `outputs/robust_ensemble.csv` — selected robust draws + their priors
- `outputs/robust_summary.csv` — per-draw seed-means for the ensemble

**Success criteria.** ≥100 robust draws. Median FSW prev in ensemble,
median nontrep_f / trep_f span — these inform the decision-analysis
sensitivity range. The ensemble's parameter region (prior values of
the robust draws) tells us which slice of 20-dim space the model
reliably occupies.

## Forward reference

Once exp 36 lands the robust ensemble: exp 37 = PN intervention
analysis on the ensemble. Each robust draw runs (PN vs counterfactual)
× 3 seeds; aggregate relative reduction in syph incidence / APO over
the ensemble for the decision-analysis posterior.
