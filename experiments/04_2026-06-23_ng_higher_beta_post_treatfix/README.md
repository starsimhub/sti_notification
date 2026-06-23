# Exp 04 — NG higher β prior, post stisim treatment-fix

**Question.** Under the stisim `fix/ng-tx` patch — which restores
`GonorrheaTreatment` to actually treating agents (exp 03's ensemble was
implicitly relying on a `rel_treat` NaN bug that made NG treatment a no-op
for ~14% of live agents at any time) — what NG `beta_m2f` range produces
an ensemble that sustains NG at endemic prevalence (~3–8% adult prev,
matching `data/zimbabwe_sti_data.csv`) through 2030–2040?

Exp 03's retained 26 draws lived in `beta_m2f ∈ [0.080, 0.295]` (median
0.158). With effective treatment restored, this range is expected to
extinct NG in most draws — single-seed probes against the exp 03 baseline
draw confirm NG → 0 across all three seeds. Exp 04 lifts the NG floor
and ceiling and re-fires the same calibration pipeline as exp 03.

**Plan.** Same 17-parameter prior as exp 03, **NG `beta_m2f` only
changed**: log-uniform [−2.30, −0.51] → [0.10, 0.60] (exp 03 was
[−3.91, −1.21] → [0.020, 0.299]). All other priors held identical. Phase
1 single-seed LHS sweep (n=500), per-disease sustainability filter (HIV
+ syph + NG + CT + TV all required to sustain 2030–2040). Phase 2:
3-seed robustness re-run on phase-1 survivors, retain draws with 3/3
sustainability on every STI.

Stisim pinned to `fix/ng-tx` at `731bc1d` (off `rc1.5.8`).

**Success criteria.**
- Phase 1 NG sustainability ≥ 50% of LHS draws (otherwise the new floor
  is still too low — try again with a higher minimum).
- Phase 2 robust ensemble ≥ 20 draws (matches exp 03's 26-draw target
  density).
- All five STIs still bracket the empirical prev band in the robust
  ensemble (not just NG; lifting NG beta shouldn't break the others).
- Endemic NG prevalence 2030–2040 inside the data envelope on the
  ensemble median.

**Out of scope.** AMR decay rates (`rel_treat_unsucc`,
`rel_treat_unneed`) are held at stisim defaults. If exp 04 fails on the
NG-sustainability criterion, exp 05 would open those.
