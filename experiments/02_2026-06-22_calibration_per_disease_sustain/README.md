# Exp 04 — calibration with per-disease sustainability

**Question.** Exp 03's 53-draw ensemble had 23/53 draws (43%) with NG
or TV `beta_m2f` < 0.05 — at or near the extinction threshold. Draw
773 was tested in scenarios and both NG and TV went extinct. The
calibration filter has been syph-only ([_pipeline.py:231](../../calibration/artifacts/scripts/_pipeline.py#L231)
prior to this experiment): `sustained = bool(new_inf > 0 AND prev_f
>= 0.001)` evaluated against the syph time series only. NG/CT/TV
were never checked.

Does requiring **all four STIs** (HIV, syph, NG, CT, TV) to sustain
the late projection window — rather than syph alone — produce a
usable ensemble against the same 17 priors as exp 03?

**Plan.** Reuse the institutional LHS pipeline at
[calibration/artifacts/scripts/run_ensemble.py](../../calibration/artifacts/scripts/run_ensemble.py),
with the per-disease sustainability flag now wired into
`_pipeline.extract_calibration_summary`. Same 17-parameter prior as
exp 03; no prior tightening this pass (we want to see what
the structural ceiling does to the new filter before tuning priors).

1. **LHS sweep** — 1000 draws over the 17-parameter prior, single
   seed. Writes per-sim summaries to `outputs/phase1_results.jsonl`.
   Includes the new per-disease sustained flags
   (`sustained_hiv`, `sustained_syph`, `sustained_ng`,
   `sustained_ct`, `sustained_tv`) and the per-disease late-window
   diagnostics (`pf_2035_2040_<d>`, `ni_2030_2040_<d>`).
2. **Multi-seed re-run** on Phase 1 candidates (sustained AND n_pass
   ≥ 5) at 3 seeds each, targeting an ensemble of ~50 draws.
3. **Selection** — sustained 3/3 AND mean n_pass ≥ 4. With the new
   stricter filter, the same acceptance criterion now requires all
   four STIs to sustain in all three seeds.
4. **Figures** — same lightweight set as exp 03 (acceptance funnel,
   pass-band hit rates, endpoint distributions, n_pass) plus a
   per-disease sustainability panel showing which STIs are most
   often the rejection reason.

**Success criteria.** A usable ensemble where every accepted draw
sustains **HIV, syph, NG, CT, TV** through the projection window in
all three seeds. Headline targets:

- **Size:** ≥ 30 draws after the 3-seed acceptance. Smaller than exp
  03's 53 is expected — the stricter filter rejects the
  near-extinction-threshold NG/TV region of the LHS.
- **No-extinction guarantee:** by construction, downstream scenario
  perturbations should not collapse NG or TV in baseline. (Scenarios
  with very high PN coverage could still push borderline draws over
  the edge; that's a scenario-side check, not a calibration check.)
- **Headline endpoint coverage** comparable to exp 03 (HIV in UNAIDS
  band; relative-effect syph endpoints in their bands; absolute syph
  prev still capped at the structural ceiling).

Failure modes worth distinguishing:

- **Pass rate < 3%:** the LHS prior is too wide for the new filter;
  next experiment tightens NG / TV `beta_m2f` lower bounds.
- **HIV becomes the rejection bottleneck:** unexpected and would
  point at an HIV model issue (not a known concern; exp 03 had HIV
  sustained almost universally).
- **Ensemble too small for scenarios (<20):** widen the LHS to
  ~1500-2000 next pass; same prior, more samples.

Cross-references: [exp 03](../03_calibration_rc1.5.7/SUMMARY.md) for
the baseline this revises; the structural ceiling on syph absolute
prev is expected to reproduce.
