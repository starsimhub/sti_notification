# Exp 13 — Trajectory selection, post-ANC-fix re-run

**Question.** Can we produce a usable posterior predictive distribution
by resampling within the post-ANC-fix NROY region from exp 09 — and
does syphilis now sustain endemic transmission through 2025 instead
of burning out the way it did in exp 10?

**Motivation.** Three things have changed since exp 10 closed:

1. The ANC screen was switched from GUD (~5% latent sensitivity) to
   era-gated serology (~90%) — commit `e3b7692`. Exp 12's coverage
   check confirmed syphilis still sustains under the new screen and
   the prior still brackets every target.
2. History matching (exp 09) was re-run against the post-fix model
   over 8 waves, reducing NROY from 91% to 1.2% of the prior volume.
3. Exp 10's pre-fix posterior showed syphilis burning through to
   near-zero active prevalence by 2020 — a structural break that
   blocked decision analysis. The diagnosis was network-driven
   burn-through, but the ANC fix changes treatment intensity over the
   same window, so the structural verdict needs re-testing on the
   updated dynamics before any FOI-floor / waning-immunity remedies
   are considered.

**Plan.**
1. Load 1000 NROY samples from `experiments/09_history_matching/nroy/hm_zim/wave8/`.
2. Run each at 10k agents, 1985–2025, **1 seed per draw** (1000 sims
   total). This matches exp 10's pre-fix configuration so the
   pre/post comparison is clean. Multi-seed within-draw variance can
   be added in a follow-up exp if ESS is adequate.
3. **24 workers, incremental JSONL writes.** The previous launch at
   75 workers drove the VM into OOM territory (~5.5 GB × 75 ≈ 410 GB
   on a 314 GB box, no swap). 24 workers caps peak at ~140 GB.
   Results are appended to `outputs/results.jsonl` one row per sim
   so any kill leaves recoverable progress.
4. Extract calibration target summary statistics from each sim.
5. Filter draws where syphilis went extinct (`syph_prev_f_2016 ≤ 0.005`).
6. Weight surviving trajectories by a Gaussian pseudo-likelihood
   across all 12 targets (same widened stds as exp 10: 2× for
   non-syph, 3× for syph).
7. Resample proportionally to produce a posterior ensemble.
8. Compute ESS, posterior predictive plots, and parameter marginals.

**Success criteria.**
- **Primary:** syphilis active prevalence is non-zero in 2020–2025 in
  the posterior ensemble — i.e. the dynamics fix held under the
  weighted posterior, not just the prior. If syphilis still burns out,
  the structural fix (FOI floor / waning immunity) flagged at the end
  of exp 10 is still required, and decision analysis stays blocked.
- **Secondary:** ESS/N > 0.05 (≥ 5% efficiency). Posterior predictive
  trajectories bracket all 12 targets including the two that exp 12
  flagged as tightening (syph sero F/M 2016).
- **Tertiary:** Parameter marginals tighter than the NROY marginals for
  the beta parameters; HIV β posterior moves off the upper edge of
  exp 10's posterior (which had pushed up against the NROY upper bound).
