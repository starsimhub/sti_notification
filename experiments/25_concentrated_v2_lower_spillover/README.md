# Exp 25 — Concentrated v2: thin the FSW→client→general bridge

**Date opened:** 2026-06-07.

**Question.** Starting from exp 24's hand-picked configuration —
which produced concentrated, sustained FSW dynamics with right stage
shares but **10× too much spillover** to the general F population
(nontrep_f 15% vs ZIMPHIA 1%, trep_f 24% vs Robyn target 4-5%) —
can we knock the spillover down 5-10× by three targeted moves while
keeping the FSW prev, sustainability, and stage shares intact?

**Hypothesis.** The bridge from FSW → clients → general F is too
fat. Three knobs control its width:

1. `structuredsexual.prop_f0` — fraction of women in lowest-risk
   pool (rg0). HIGHER = more women insulated from the bridge.
   Exp 24 had this **wrong-direction** at 0.55; bump to 0.85.
2. `structuredsexual.m1_conc` — mid-risk male concurrency. Lower
   shrinks the bridge mid-risk men provide between FSW and general F.
   Exp 24 at 0.20; drop to 0.05.
3. `client_shares` — Bernoulli p that any male becomes a client.
   Lower = fewer men carry syph back to the general F pool.
   Exp 24 used default 0.20; drop to 0.15.

Everything else from exp 24 stays. See
[`../24_concentrated_sustained_handpick/SUMMARY.md`](../24_concentrated_sustained_handpick/SUMMARY.md)
for the structural finding that motivates the iteration.

**Plan.**

Same hand-picked configuration as exp 24 except three changes above.
Same diagnostics: per-seed summary, stage-share CSV, time-series
pickle. 3 seeds, ~3 min wall clock.

**Success criteria.** Same as exp 24's primary set, plus Robyn's
refined ZIMPHIA-context targets:

| Target | Range | Source |
|---|---|---|
| FSW prev 2019 | [0.20, 0.40] | UNAIDS 2019 (~30%) |
| nontrep_f 2016 | [0.004, 0.016] | ZIMPHIA dual-positive (1%) |
| trep_f 2016 | [0.027, 0.05] | ZIMPHIA total seroprev (2.7%, possibly up to 5%) |
| Primary stage share | [0.50, 0.65] | Expert opinion |
| Secondary stage share | [0.25, 0.40] | Expert opinion |
| Sustained to 2040 | new_inf > 0 | Project goal |

**Decision branches.**

- **All targets pass** → open exp 26 = tight LHS coverage check
  (50-100 draws over narrow ranges around this config) to feed HM.
- **trep_f passes but FSW prev misses low** (we cut spillover too
  hard and FSW pool collapsed) → relax one of the three knobs
  (probably client_shares back to 0.18-0.20).
- **trep_f still high** → spillover knobs aren't enough; need
  to add an explicit dampener (e.g. lower rg0 partner change rate,
  or a stable-partner-only behavior for rg0).
- **Stage shares drift** → unlikely given exp 24's stability there,
  but if they do, reconsider; otherwise note and continue.

**What this experiment does NOT do.**

- Not a sweep. Single configuration, 3 seeds.
- Does not open new priors.
- Does not change the disease natural-history code.
- Does not change ANC ramp (still defensible peak 0.70 by 2018).
- Does not change the boosted care-seeking CSV.
