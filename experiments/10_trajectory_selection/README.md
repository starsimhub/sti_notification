# Exp 10 — Trajectory selection within NROY

**Question.** Can we produce a posterior predictive distribution over
trajectories by resampling within the NROY region from exp 09?

**Motivation.** History matching (exp 09) narrowed the prior to 0.85%
of the original volume. The NROY constrains disease betas well but
cannot handle syphilis bimodality (sustain vs. extinct). Trajectory
selection handles this naturally: run full simulations from NROY draws,
filter extinct syphilis runs, and weight the surviving trajectories by
a pseudo-likelihood against all targets.

**Plan.**
1. Load NROY samples from exp 09 wave 8.
2. Draw 1000 parameter sets from the NROY region.
3. Run each at 10k agents with 3 seeds per parameter set (3000 total
   sims) to estimate run-to-run variance.
4. Extract all calibration target summary statistics.
5. Filter: drop sims where syphilis went extinct (prevalence_f < 0.001
   at 2016).
6. Weight surviving trajectories by a Gaussian pseudo-likelihood across
   all targets.
7. Resample proportionally to produce the posterior ensemble.
8. Compute ESS (effective sample size) — the key diagnostic.

**Success criteria.** ESS/N > 0.05 (at least 5% efficiency). Posterior
predictive trajectories bracket all targets. Posterior parameter
marginals are tighter than NROY marginals for at least the beta
parameters.
