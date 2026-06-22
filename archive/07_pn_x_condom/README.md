# Exp 07 — PN × condom combined grid

**Question.** Exp 05 and 06 showed PN and condoms move CT *orthogonally*
(PN ↓ prevalence at flat incidence; condoms ↓ incidence). Do they
**combine** — does the high-PN × high-condom corner achieve both low
prevalence *and* low incidence, and is the joint effect roughly additive
or is there interaction?

**Plan.** POC arm, draw 773, 1 seed, CT, window 2030–2034. A 3×3 grid:
PN coverage multiplier ∈ {×1, ×3, ×8} crossed with condom-counselling
coverage ∈ {0, 0.5, 1.0} (eff 0.5, 6-mo window, as exp 06). 9 cells.
Endpoints per cell: CT prevalence (window mean), CT incidence, cohort
reinfection. Reuses exp 04 `STIChainTracer` + exp 06 `CondomCounseling`.

**Success criteria.** Heatmaps of CT prevalence and incidence over the
grid. Expect the (×8, 1.0) corner to sit lowest on *both* axes — PN
supplying the prevalence drop, condoms the incidence drop. Quantify
additivity: compare the combined-cell reduction to the sum of the
single-lever reductions from the (×1, 0) base. Still 1 draw — directions
only; the ensemble (post-recalibration) gives magnitudes.
