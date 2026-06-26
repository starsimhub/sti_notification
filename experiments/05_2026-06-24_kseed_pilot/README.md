# Exp 05 pilot — K=5 sim averaging, no filter

**Question.** Before committing to a full recalibration under the
"single-phase K=5 seeds, mean-in-band filter" reframing, verify mutual
understanding. Run 20 LHS draws from the exp 04 prior, K=5 seeds each,
average each draw's metrics across its 5 seeds, report results
**without applying any filter or threshold**. The point is to look at
the per-draw means + per-seed spreads and confirm the proposed approach
behaves the way both of us expect before scaling to 500 draws.

**Plan.** 20 LHS draws from the exp 04 prior (`priors.calib_pars`,
NG `beta_m2f` ∈ [0.10, 0.60]). K=5 seeds per draw (`seed = draw_idx
× 1000 + sub_idx`). 100 sims total on 60 workers (~3 min wall). For
each draw: report the K=5 individual seed values for each calibration
target + the mean across seeds. Output a table; no figures, no
thresholding, no candidate selection.

Stisim pinned to `fix/ng-tx@731bc1d`.

**Success criteria.** Pilot is informational, not decisional. Looking
for:
- Within-draw seed spreads to be modest (~CV 0.05–0.15 on key metrics)
  for most draws, with a few high-variance "drama" draws that mix
  extinct + sustained seeds.
- Per-draw means to span a sensible range across the empirical bands
  (some draws hot, some cold, some on-target).
- No catastrophic crashes.

The pilot informs three open design calls before we lock the spec
(threshold ≥4 vs ≥5 bands, whether to revisit any prior, whether K=5
is enough). Out of scope: filtering, retention decisions, beta
posteriors — that all lives in the full exp 05 once the pilot
confirms the approach.
