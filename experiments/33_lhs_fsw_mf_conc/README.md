# Exp 33 — LHS with FSW MF-concurrency multiplier

**Question.** Exp 32's transmission matrix showed FSW carry 8% of
plateau-era transmissions to non-client males (F_fsw → M_other),
which then feeds general-population circulation (M_other → F_other ≈
12%). The model has a self-sustaining general-pop transmission
engine (~32% of plateau transmissions) that sits outside the
FSW-client core. If we reduce FSW participation in non-commercial
partnerships — but not eliminate it — does the general-pop engine
collapse, or does it self-sustain via residual M-F circulation?

**Plan.**

1. **stisim patch** (small, defensive). Add
   `fsw_mf_conc_mult` parameter to `MFPars` (default 1.0 = no
   effect). Applied inside `MFNetwork.set_concurrency` after the
   risk-group loop, multiplies the FSW agents' concurrency `mu`
   only on networks that expose `self.fsw`. No effect on pure
   `MFNetwork`, no effect at default 1.0.

2. **Open as 17th prior** with range [0.1, 1.0]: from "FSW partner
   90% less in non-commercial settings" to "no change."

3. **Re-run 300 LHS** at exp 32's setup (single seed, 10k agents,
   1985-2040). Re-uses the analyzers (HIV-stratified coinfection +
   SyphTransmissionEvents) already wired into model.py.

4. **Score against the same 9 targets** as exp 32 for direct
   comparability — relaxed nontrep [0.01, 0.05], plus HIV-stratified
   absolute + ratio.

5. **Diagnostic focus.** Beyond hit-count, the headline question is
   whether the transmission matrix changes shape in the top
   cluster: does F_fsw → M_other actually drop? Does M_other →
   F_other drop in step? Does general-pop trep drop without losing
   FSW prev?

**Success criteria.**

- **Best case.** ≥ 1 draw passes 7+/9 targets — the lever closes
  the gap and we have a single-config baseline.
- **Plausible.** The 5+/9 cluster grows substantially (vs exp 32's
  36 draws) and the typical `nontrep_f` drops from ~0.10 toward the
  0.05 band ceiling. Even without 7+/9 passes, this is a
  structural improvement.
- **Informative negative.** The cluster doesn't grow and `nontrep_f`
  doesn't drop. Means the general-pop M↔F engine is self-sustaining
  independent of FSW seeding — narrows the structural diagnosis to
  the M↔F partnership rates themselves.

**Acceptance.** Whichever way it lands, we extract a clean
mechanistic answer about whether the FSW→non-client→general-F
channel is load-bearing in the general-pop engine, plus an updated
transmission matrix in the top cluster.

## Why not also restrict FSW age range or stop FSW M-M partnerships

Concurrency is the single cap on simultaneous MF partnerships, so
reducing it covers stable + casual + one-off together — exactly the
"FSW participate a bit LESS in casual and one-off" the analysis
suggested. Restricting FSW age range or partnership types directly
would require more invasive changes for marginal additional benefit.

## Forward reference

If exp 33 produces ≥ 1 viable draw: exp 34 focuses analysis on the
top draw (Lorenz, transmission matrix, behavioural composition).

If exp 33 is an informative negative: exp 34 is either (a) the M↔F
general-pop engine fix (concurrency reductions on rg1 men), or
(b) accept the 5+/9 cluster as the decision-analysis ensemble.
