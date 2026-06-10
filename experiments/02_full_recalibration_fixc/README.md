# Exp 02 — Full recalibration on Fix C corrected baseline

**Question.** Given [exp 01](../01_coverage_check_fixc/SUMMARY.md)'s
verdict that Fix C improves the policy-relevant active-disease metric
(nontrep+ -32%) while preserving HIV calibration, run the full
two-phase LHS pipeline against the corrected model to produce a new
robust ensemble. Goal: ~200 robust draws that pass sustainability +
target band filters, matching the structure of
`archive/calibration-2026-06`'s exp 40.

**Plan.**

- Reuse [`calibration/artifacts/scripts/run_ensemble.py`](../../calibration/artifacts/scripts/run_ensemble.py)
  with `--phase all` against the existing `priors.py` (no prior
  changes — exp 01 showed the prior is broad enough).
- **Phase 1:** 2000 LHS draws × 1 seed. Filter sustained AND n_pass ≥ 5
  of 9 targets → ~120 candidates (scaled from old calibration's 5000-draw
  yield).
- **Phase 2:** 3-seed robustness re-run on candidates. Filter sustained
  3/3 AND mean n_pass ≥ 4 → target ~200 robust draws.

**Success criteria.**

- ≥ 150 robust draws produced (matches the "usable ensemble" target
  from the old calibration).
- HIV calibration stays in band (whole-pop median 9–13% over
  2010–2020).
- Nontrep+ ensemble median ≤ 8% (improving on the 50-draw prior
  predictive sustained median of 8.6%).
- Stage shares (primary / secondary / latent) in plausible bands.

**Acceptance criteria for downstream use** (per
`calibration/methodology.md`): HIV in band; HIV+/HIV− trep ratio
[3.0, 6.0] for ≥80% of draws; syph stage shares plausible; NG/CT/TV
medians in surveillance bands.

**Expected wall time:** ~50 min Phase 1 (2000 sims @ ~88s/sim on 60
workers) + ~15 min Phase 2 = ~1.1h total. Running on the 80-core AMD
EPYC VM at 60 workers (75% utilisation, headroom for other users).
Trade-off vs the old 5000-draw calibration: fewer LHS draws means
fewer Phase-1 candidates, which may reduce the final robust ensemble
below 200. If yield is too low we can extend Phase 1 with more draws
using a different LHS seed.
