# Exp 34 — LHS with general-population network levers

**Question.** Exp 33 confirmed the residual structural gap lives in
the self-sustaining M↔F general-population transmission engine, not
in the FSW-to-non-client channel. Three knobs that act directly on
that engine are still fixed in code (not exposed as priors):

- `syph.rel_trans_latent_half_life` (currently 6 months) — controls
  how long latent-stage adults remain infectious. Longer half-life =
  more long-tail transmission carrying low-grade prev forward.
- `structuredsexual.f1_conc` (currently 0.15) — medium-risk women's
  casual concurrency rate.
- `structuredsexual.m2_conc` (currently 4.4) — clients'
  concurrency rate (governs how many partners clients carry).

If any combination of these knobs, together with the 17 priors from
exp 33, produces a sustained draw inside the ZIMPHIA target band,
we've found the structural fix. If not — over 20 LHS dimensions with
all the relevant levers exposed — the parameter-only calibration is
provably exhausted and the architecture itself is the bottleneck.

**Plan.**

1. Add three new priors to `priors.py`:
   - `syph.rel_trans_latent_half_life`: linear [0.25, 2.0] years
   - `structuredsexual.f1_conc`: linear [0.05, 0.30]
   - `structuredsexual.m2_conc`: linear [2.0, 8.0]

2. `set_pars_local` handles the new half-life par as an `ss.years()`
   dur object (analogous to `time_to_undetectable`); other two are
   plain floats. Small one-line patch to exp 24's run.py.

3. **Pre-filter or score on sustained.** Robyn's rule: we never
   accept a decaying draw, even if it lands in the target band at a
   single year. Continue scoring with the same 9 targets, but treat
   the cluster "**sustained AND in (relaxed) target band**" as the
   target dataset rather than "5+/9 pass" — to weed out the
   decay-through-band draws exp 33 identified.

4. Run 300 LHS over 20 priors, single seed each. Same setup
   otherwise. Expected ~13 min total.

5. Diagnostic focus: among **sustained** draws, what's the lowest
   achievable `nontrep_f` / `trep_f`? Does any sustained draw enter
   the relaxed target box [0.01, 0.05] × [0.05, 0.10]? If a cluster
   exists, what are its characteristic parameter values?

**Success criteria.**

- **Best case.** ≥ 1 sustained draw lands in (or near) the relaxed
  nontrep × trep target box. The model can match ZIMPHIA absolute
  prev with the new levers — calibrate-around-this-cluster is now
  possible.
- **Plausible.** Sustained draws shift toward the band even if none
  enter — e.g. sustained nontrep_f median drops from 0.124 (exp 33)
  to 0.08-0.10. Some structural movement; ensemble framing still
  viable.
- **Informative negative.** No sustained draws move below
  nontrep_f ≈ 0.10 regardless of half-life, f1_conc, or m2_conc.
  Parameter-only calibration is provably exhausted in 20 dims; the
  bifurcation between sustained-hot and decay is intrinsic to the
  network architecture. Time to commit to the ensemble-from-existing
  cluster path with a tight diagnostic writeup.

## Why these three knobs

- **rel_trans_latent_half_life.** The half-life controls how long
  late-stage trep+ adults still feed transmission. Longer half-life
  = more general-pop trep buildup over time. Currently 6 months —
  on the short end of WHO Europe's "early latent ≈ 1 year"
  threshold. Range [0.25, 2.0] yr spans plausible bounds.

- **f1_conc.** Medium-risk women carry the majority of general-pop
  trep+ accumulation. Currently 0.15 — symmetric with the M1
  concurrency prior. Opening allows the LHS to test whether
  reducing F1 concurrency cuts the general-pop engine without
  killing FSW dynamics.

- **m2_conc.** Clients currently carry 4.4 concurrent partners on
  average. That's high — drives both the FSW→client→wife pathway
  *and* the client→F_other leak. Range [2.0, 8.0] tests whether
  more concentrated clients (high conc, fewer of them carrying more
  acts) or more dilute clients change the calibration.

## Forward reference

If exp 34 produces a sustainable draw in target band: exp 35 is a
focused single-config analysis (Lorenz, transmission matrix,
sensitivity) on the new operating point.

If exp 34 is informative negative: exp 35 is the ensemble write-up
combining exp 32 + 33 + 34 sustained 4+/9 draws as the
decision-analysis dataset, with the structural mismatch documented
as a methods limitation.
