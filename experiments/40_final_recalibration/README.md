# Exp 40 — Final recalibration with marital coital-decay + client wife displacement

**Question.** With three bundled fixes targeting the three identified
calibration misses from [exp 39](../39_pub_figures_baseline_pn/SUMMARY.md)
(HIV 5pp hot whole-pop / 6pp hot 15-49; syph trep+ 5-10× hot; CT 5×
under), can we produce an ensemble where:

- HIV whole-pop prev within 2pp of UNAIDS at 2016
- HIV 15-49 prev within 3pp of ZIMPHIA (15.9% in 2016, 14.8% in 2020)
- Syph trep_f within 2× of ZIMPHIA (5.0-10.0% target)
- CT F 25-29 prev within ±5pp of surveillance (~12% data)

If we miss after this attempt, we accept the model as-is and write up
the calibration limitations honestly.

**Plan — three bundled fixes:**

1. **New structural mechanism in stisim** (`feat/marital-act-decay`
   branch): linear coital decay on stable edges (`stable_act_decay`)
   AND client-husband marital-act multiplier (`client_marital_act_mult`).
   Both target the M_client → F_other_via_stable leakage route, which
   was 14% of all syph transmissions in exp 38 with no available
   knob.
2. **HIV recalibration knobs**: `hiv.beta_m2f` upper tightened from
   0.05 → 0.03 (exp 38 median was 0.013, comfortably in new range);
   `hiv.rel_init_prev` opened in [0.3, 1.5] for the level shift.
3. **CT range raised**: `ct.beta_m2f` from [0.02, 0.30] → [0.05, 0.50].

Plus: drop the two PN priors (`pn.p_notify_*`) — max|r| ~0.06 in
exp 38, washed out at LHS scale. Baseline PN stays on at default
0.20/0.10 stable/casual notify rates.

**Net prior space: 19 priors** (16 from exp 38 minus 2 PN, plus 1
HIV init plus 2 new structuredsexual).

**Phasing.**

- Phase 1: 1500 LHS draws, seed=45 (fresh; orthogonal to seeds 42-44),
  single seed each. ~70 min wall.
- Filter: sustained AND n_pass ≥ 5. Backfill from n_pass==4 if needed.
- Phase 2: each selected candidate × 3 seeds. ~50-70 min wall.
- Optional backfill ~10 min.

**Expected total wall time:** ~2.5 hr.

**Success criteria** (see Question section). If we hit:
- Move to exp 41: regenerate publication figures from the new ensemble
  (exp 39-style pipeline against exp 40 outputs).
- Open PN-intervention scenarios as exp 42+.

If we miss: write up the calibration limitations and proceed with
the existing exp 38 ensemble for the PN scenarios, accepting that
the model's absolute levels are off.

## Forward reference

After this lands, re-run exp 39-style figure pipeline on the new
ensemble (will be exp 41).
