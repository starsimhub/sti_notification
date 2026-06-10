# Exp 01 — Coverage check on corrected baseline (Fix C two-channel syph dx)

**Question.** Before launching a full recalibration, confirm that the
corrected model (Fix C, [PR #5](https://github.com/starsimhub/sti_notification/pull/5))
can produce the Zimbabwe data — UNAIDS HIV, ZIMPHIA 2015–16 syphilis
(trep+ 2.7% / nontrep+ 0.8%), surveillance NG/CT/TV — under the
calibration prior in [`priors.py`](../../priors.py). This is the
prior predictive check that gates the recalibration pipeline.

**Background.** The previous calibration (200-draw ensemble on
`archive/calibration-2026-06`) was invalidated by Fix C, which
restructured the syph syndromic-management baseline into two channels
(ulcer + rash) with semantically correct presumptive products. The
structural shift moves FSW syph prev meaningfully (+14pp on a single
diagnostic draw), so we cannot assume the prior region that fit
ZIMPHIA before still covers the data now.

**Plan.**

- 50 LHS draws from the existing `priors.py` (19 params), 1 seed
  each. Reuses [`calibration/artifacts/scripts/_pipeline.py`](../../calibration/artifacts/scripts/_pipeline.py)
  for prior sampling + sim construction.
- Extract annualised time series for HIV, NG, CT, TV, syph (trep+,
  nontrep+, FSW prev, syph age × sex if cheap).
- Compute ensemble quantiles + overlay surveillance data on figures.
- Inspect coverage: is every observed data point inside the 5–95%
  envelope?

**Success criteria.**

- **Covered:** every UNAIDS HIV point, ZIMPHIA syph point, and NG/CT/TV
  surveillance point lies inside the 5–95% envelope of the 50-draw
  ensemble. Proceed to full recalibration.
- **Mostly covered, edges miss:** a handful of points outside,
  especially at peaks or troughs. Document in SUMMARY, proceed but
  note which targets to watch in calibration.
- **Systematically outside:** prior is too narrow or model can't reach
  the data with the corrected baseline. Stop, decide between widening
  the prior or further model fixes before recalibration.

**Compute.** 50 sims × ~90 s / 24 workers ≈ 4 min wall.
