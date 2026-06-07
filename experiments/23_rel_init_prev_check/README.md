# Exp 23 — Initial-condition sensitivity + stratified diagnostic

**Date opened:** 2026-06-06.

**Question.** Two linked questions in one experiment:

1. **Is the ~15% endemic floor an attractor of the model dynamics, or
   an artifact of seeding the FSW pool too hot in 1985?** If we let
   `syph.rel_init_prev` vary over a wide log range (down to ~10x
   below the current fixed 0.2 baseline), does any draw equilibrate
   into the ZIMPHIA acceptance band [0.4%, 1.6%]?
2. **Among sustaining draws, what sub-population pins the floor?**
   What fraction of plateau-era new infections (2010-2030) come from
   FSW + clients vs the general F/M population, vs the structured-
   network risk groups 0/1/2 × sex?

**Why now.** Exp 22 closed with a clean bifurcation finding: every
sustainer settles at ~15% detect_f regardless of β, care-seeking, or
network-shape priors. Two complementary hypotheses for why:

- **(A) The floor is a true attractor of the deterministic skeleton**
  — set by FSW reservoir + stage-specific transmission dynamics — and
  no initial condition can land us in a low-prev basin. If so, the
  fix is structural (FSW network, primary-stage transmission, stage
  durations).
- **(B) The floor reflects the initial condition.** With
  `rel_init_prev = 0.2` baseline, FSW are seeded at ~2% latent in
  1985. If that seed is above what the FSW reservoir would naturally
  sustain, the model converges to a "still hot" basin from above and
  never samples the low basin it might have if seeded lower.

The cheapest test is to put `syph.rel_init_prev` into the prior over
a wide log range and ask whether the low-prev corner opens up. While
we're at it, enable the syph module's risk-group + FSW result
storage so every sustainer gets a free attribution of new infections
by sub-population. See
[`../22_anc_sustainability_check/SUMMARY.md`](../22_anc_sustainability_check/SUMMARY.md)
for the closing analysis, [[project_calibration_goal_ensemble]] for
the broader goal, and [[feedback_calibration_guards]] for why we
always plot time series + check coverage at multiple metrics.

**Plan.**

1. **Extended prior.** Added `syph.rel_init_prev` ∈ (0.02, 1.00) on
   log scale to `priors.py` — wide enough that "seeded 10× below
   current baseline" is in scope. Prior is now 13-dim.
2. **Enable stratified result storage** on the syph module before
   `sim.init()`: `store_sw = True`, `store_risk_groups = True`.
   This gives us per-step `new_infections_sw`,
   `new_infections_not_sw`, `new_infections_client`,
   `new_infections_not_client`, and
   `new_infections_risk_group_{0,1,2}_{female,male}` for every draw
   with no extra runtime cost.
3. Generate 150 LHS draws over the 13-dim prior (seed=42), run each
   to 2040 at 10k agents, 24 workers. Inherits all exp 22 v3 model
   + intervention fixes (low-ANC PoC ramp, SyphilisANCTimer,
   `dt_scale=False` on syph_symp_test).
4. Capture: same summary metrics as exp 22 + the stratified
   new_infections series for every draw.

**Configuration.**

- 150 LHS draws × 1 seed = 150 sims.
- 10k agents, 1985-2040, 24 workers, maxtasksperchild=10.
- Same low-ANC PoC values as exp 22 v3 (anc_probs =
  [0.05, 0.10, 0.15, 0.15, 0.20, 0.20, 0.20]) — NOT defensible for
  realistic ZW coverage; held constant here only to isolate the
  rel_init_prev effect from the ANC effect already studied in 22.

**Success criteria.**

**Primary — the low-prev corner test.** At least one sustaining draw
lands inside the ZIMPHIA detect_f band [0.4%, 1.6%]. A handful (≥5)
would be a strong positive result and would shift the calibration
story significantly. **0 again** closes out hypothesis (B) and
confirms hypothesis (A): the floor is structural, not seeding-
dependent.

**Secondary — sub-population attribution among sustainers.** The
stratified `new_infections_*` results during 2010-2030 are
interpretable per draw. A clear pattern across sustainers (e.g.
"≥60% from FSW + clients in every draw") points us to the next
candidate structural lever.

**Tertiary — non-syph targets bracket data.** Sanity check; nothing
about this experiment should change HIV/NG/CT/TV behavior.

**Decision branches.**

- **If primary succeeds (≥1 sustainer in band)** → close exp 23,
  open exp 24 = focused sweep over `rel_init_prev` and any other
  parameters the low-prev sustainers concentrated in, with realistic
  ANC restored, looking for a defensible calibration corner.
- **If primary fails (0 in band)** → hypothesis (B) is closed out.
  Use the stratified results from this run to attribute the floor to
  a sub-population, then open exp 24 = focused sensitivity on
  whichever structural component dominates (FSW network share /
  duration, risk-group 2 transmission, primary-stage rel_trans).

**What this experiment does NOT do.**

- Does not change interventions, networks, or model code.
- Does not change ANC ramp (still PoC low values for comparability
  with exp 22 — realistic ramp will be tested separately once the
  bifurcation question is answered).
- Does not run HM.
