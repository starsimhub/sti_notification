# Exp 32 — LHS with HIV-stratified syph + connector lever

**Question.** Exp 30 ran 300 LHS draws over 14 priors and found **0
draws** passing 6+ of 7 targets — but those targets didn't include
HIV-stratified syphilis prevalence. ZIMPHIA 2015-16 reports HIV+
adults at 7.1% trep and 2.9% active vs HIV- at 1.9% / 0.4% — a
3.7×/7× gradient that's the strongest empirical signal in the table.
The model's HIV→syph connector defaults `rel_sus_syph_hiv=1` and
`rel_trans_syph_hiv=1`, so it has no mechanism to produce that
gradient mechanically beyond shared networks.

This experiment opens those two connector parameters as priors and
re-sweeps with HIV-stratified targets added.

**Plan.**

1. Add to `model.py` (general-purpose, stays on downstream):
   - Two coinfection_stats analyzers — one tracking `syph.trep`, one
     tracking `syph.nontrep` — both at `age_limits=[15, 64]` to
     match ZIMPHIA exactly.
   - A transmission-event recorder analyzer that monkey-patches
     `syph.set_prognoses` to log `(ti, source_uid, source_stage,
     dest_uid, network_key)` for each syph transmission. Output
     buffered, dumped to `outputs/events_*.parquet` per sim. Needed
     for Lorenz, transmission matrix, behavioural-mixture analysis
     downstream.

2. Add to `priors.py` (16 priors total):
   - `hiv_syph.rel_sus_syph_hiv`: 1.0–3.0, log-scale.
   - `hiv_syph.rel_trans_syph_hiv`: 1.0–2.5, log-scale.

3. Run 300 LHS draws × 1 seed. Same scale as exp 30 for direct
   comparability. Top candidates that pass 7+/9 get seed expansion
   in a focused follow-up to stabilize the small-N HIV-stratified
   numerators (HIV+ trep+ at ~5% × ~15% HIV-prev × 10k agents ≈ 75
   cases per sim).

4. Score against 9 targets (7 from exp 30 + 2 new HIV-stratified):
   - FSW prev 2019 ∈ [0.20, 0.40] (unchanged)
   - nontrep_f 2016 ∈ [0.01, 0.05] (**relaxed** from exp 30's
     [0.01, 0.03] to give the HIV-coupling lever room to act without
     auto-disqualifying)
   - trep_f 2016 ∈ [0.05, 0.10] (loose ZIMPHIA trep)
   - Primary share of new transmissions ∈ [0.45, 0.65]
   - Secondary share ∈ [0.25, 0.45]
   - Early-latent share ≤ 0.15
   - Sustained (mean new_inf 2030-2040 > 0)
   - **NEW** HIV+ trep 2016 ∈ [0.05, 0.09] (absolute HIV+ band)
   - **NEW** HIV+/HIV- trep ratio 2016 ∈ [3.0, 6.0]

5. Analyze. Three-panel hit-count + scatter set parallel to exp 30,
   plus a new HIV+/HIV- panel.

**Success criteria.**

- **Best case.** ≥ 1 draw passes 7+/9 targets including both HIV
  stratification cells. This is the new "definitive pass" — opens a
  path to a single-config baseline that anchors decision analysis.
- **Plausible.** A cluster of 5-10 draws passing 6/9 — including the
  HIV stratification — emerges. This becomes the ensemble seed.
- **Negative result.** Even with `rel_sus_syph_hiv` and
  `rel_trans_syph_hiv` opened, no draw reaches 7+/9. Structural
  conclusion: HIV-syph coupling alone doesn't bridge the FSW-to-
  general-F leak, and the architecture itself (network mixing,
  partnership durations) is the residual bottleneck. Justifies
  moving to behavioural-mixture / ensemble framing for decision
  analysis.

**Acceptance.** Whatever the result, this is the calibration story
we tell: full prior space (16 dimensions), full target set (9
including HIV stratification + transmission shape), 300 draws.
Generates the full event log per draw so subsequent mechanistic
analysis (Lorenz, transmission matrix, behavioural mixture) is
ready without rerunning.

## Why not just re-run exp 30 top draws

Exp 30's top draws were selected against 7 targets without HIV
stratification. The new connector levers (`rel_sus_syph_hiv`,
`rel_trans_syph_hiv`) weren't part of that prior space. Re-running
the exhausted parameter space doesn't test the new lever. Fresh LHS
is the honest test of "can the augmented model produce ZIMPHIA's
HIV-syph gradient?"

## Forward reference

If exp 32 produces ≥ 1 viable draw, the next experiment is a
focused analysis of its transmission-event log (Lorenz, transmission
matrix, behavioural-subgroup composition) — exp 33 will be defined
once exp 32's results land.

If exp 32 fails, the next experiment shifts to behavioural-mixture
ensemble framing using exp 32's 5-6/9-pass cluster.
