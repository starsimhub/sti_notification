# Exp 26 — m1_conc sweep (find the sweet spot)

**Date opened:** 2026-06-07.

**Question.** At the v3 base config (`prop_f0=0.85`,
`client_shares=0.20` reverted from exp 25, everything else from
exp 24 v1), what value of `structuredsexual.m1_conc` lands the
epidemic in a concentrated-sustained state — FSW prev ~30%,
nontrep_f ~1%, trep_f ~3-5%, primary-dominant?

**Why now.** Exp 24 (m1_conc=0.20) had FSW=0.40 with too much
general spillover (nontrep_f=15%). Exp 25 (m1_conc=0.05 +
client_shares 0.20→0.15) collapsed. The collapse-trajectory
passed through nontrep_f ≈ 0.4% — exactly in the data band —
on its way down, suggesting the right configuration is between
the two. Robyn's intuition: m1_conc "a little higher" than 0.05
should hit it.

See [`../25_concentrated_v2_lower_spillover/SUMMARY.md`](../25_concentrated_v2_lower_spillover/SUMMARY.md)
for the over-correction diagnosis and the asymmetric-bridge framing.

**Plan.**

Sweep `m1_conc` over **{0.05, 0.08, 0.10, 0.12, 0.15, 0.20}** — six
values, three seeds each = 18 sims, run in parallel on 18 workers
(~3 min wall clock).

Everything else fixed at exp 24's hand-pick with the v3 fix
(`prop_f0` lifted, `client_shares` kept):

| Knob | Value |
|---|---|
| `structuredsexual.prop_f0` | **0.85** (v3 fix vs exp 24's 0.55) |
| `structuredsexual.client_shares` | 0.20 (exp 24 / stisim default) |
| `structuredsexual.dur_sw` | 15y |
| `syph.p_symp_primary_f` | 0.50 |
| `syph.p_symp_primary_m` | 0.80 |
| `syph_symp_test.rel_test` | 1.30 |
| `syph.beta_m2f` | 0.20 |
| `syph.time_to_undetectable` | 20y |
| `syph.rel_init_prev` | 0.20 |
| ANC ramp | defensible (peak 0.70 by 2018) |
| Care-seeking CSV | exp 24's boosted version |
| `hiv/ng/ct/tv.beta_m2f` | exp 24 values |

Per [[feedback-stage-share-check]]: every sim still reports
by-stage transmission shares.

**Success criteria.**

For each m1_conc value, compute 3-seed-mean of:
- FSW prev at 2019 (target [0.20, 0.40])
- nontrep_f at 2016 (target [0.004, 0.016])
- trep_f at 2016 (target [0.027, 0.05])
- Primary stage share (target [0.50, 0.65])
- Secondary stage share (target [0.25, 0.40])
- Sustainability (new_inf > 0 in 2030-40)

**Sweet spot** = a value where ≥5 of 6 targets land in band.

Expectation: monotone-ish trends.
- FSW prev: mildly increasing in m1_conc (more bridge → more reinfection)
- nontrep_f / trep_f: strongly increasing in m1_conc (more spillover)
- Stage shares: stable around primary 60%, sec 35%

**Decision branches.**

- **Clean sweet spot exists** → use it as exp 27's center for a tight
  LHS coverage check (50 draws) over narrow ranges, feeding HM.
- **No value bridges FSW band AND nontrep band** → the bridge is
  inherently asymmetric in a different way; iterate on either
  `prop_f0` or another network knob.
- **Sustainability fails at low m1_conc but everything else is
  marginal** → revisit `client_shares` or `dur_sw` to add more
  FSW R₀ headroom.

**What this experiment does NOT do.**

- Not a full LHS sweep — single parameter only.
- Does not open any new priors.
- Does not change the disease natural-history.
- Does not change ANC ramp or care-seeking CSV.
