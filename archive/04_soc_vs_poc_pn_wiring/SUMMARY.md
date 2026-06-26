# Exp 04 — SOC vs POC+PN wiring check — SUMMARY

**Scope.** One calibrated draw (`draw_idx=773`, median-n_pass of the rc1.5.7
ensemble), one seed, two arms: **A** = SOC (syndromic VDS/UDS + syndromic
GUD + baseline PN) vs **B** = POC etiological dx for VDS+GUD + PN scaled
×3. Agent-level chain trace of a cohort of 100 successfully-treated index
cases, 12-month follow-up, window 2030–2034. Built on the validated
`_pipeline` path (load draw → `set_pars_local` → edge-stratified
`pn_rates`).

**Traced disease pivoted NG → CT.** In draw 773 **NG and TV are extinct**
(prev→0; NG ≈120 real agent-infections over 55 yrs) — the discharging-STI
betas were never calibration targets (only syph + HIV + FSW were), so they
are free priors and swing by draw. **CT** sustains (19% prev) and its
treatment cures (~89%), so it is the discharging STI on which PN chains are
observable here. NG's behaviour is therefore **untested** in this draw.

## Result

**The PN cascade is wired correctly, end-to-end.** Verified at the agent
level: index treated → concurrent partners walked → notified → attended →
POC-tested → treated → cured. The mechanism notifies *all* concurrent
partners independently (e.g. index 2222 notifies 2 of 3 partners in one
step), not just one.

**POC+PN (B) beats SOC (A) — but modestly.** (CT, 2030–34)

| metric | A (SOC) | B (POC+PN×3) |
|---|---|---|
| CT prevalence (window mean) | 0.193 | 0.182 |
| cohort reinfected /100 | 52 | 45 |
| PN partners attending | 0.44M | 2.74M (6.3×) |
| CT cures | 3.12M | 4.66M |

A 6.3× increase in PN attendance buys ~6% relative prevalence reduction.
CT incidence is *higher* in B (11.5M vs 8.9M new infections) — more
treatment shortens infectious duration (↓prevalence) and speeds S→I→S
cycling.

## Observations (the mechanism)

1. **Not sex-work-driven (for CT).** ~80% of all CT transmission, and
   ~90% of cohort reinfections, come from **regular partners**
   (`f_other`/`m_other`); only ~20% transactional (FSW+client); **0**
   cohort reinfections from FSW/clients. The sex-work-reservoir hypothesis
   is rejected for CT (it may still hold for NG — untested).

2. **Reinfection is from the index's own concurrent partners going
   untreated** — not new/prior partners, not an external reservoir.
   ~90% of reinfection sources were a known concurrent partner *at
   treatment time*. The leak is **coverage**: reinfected indices had ~1.5
   concurrent partners but only **0.19 (SOC) / 0.69 (POC×3)** were
   notified. Scaling PN ×3 raised coverage and cut untreated-partner
   reinfections (45→24 of the known-partner reinfections), confirming PN
   *can* address this — it is not structurally blocked.

3. **Residual floor in B:** ~16 of B's 45 reinfections came from partners
   who *did* attend (11% treatment failure + one-step treatment delay +
   re-acquisition) — a floor PN reach alone cannot clear.

## Corrections to prior notes

- **exp 01 "NG-NaN cure bug" is not material here.** `ng_tx.rel_treat`
  NaN fraction is 0.09%; CT cures at 88.9%. The "0% NG cure" in this draw
  is just NG being extinct (treatments land on susceptibles =
  unnecessary), not a treatment bug.
- Initial claims of "PN doesn't help" (from arm B alone) and "reinfection
  from a broad web PN can't reach" were both wrong, corrected by the A-vs-B
  contrast and the source attribution respectively.

## Caveats

- **1 draw, 1 seed.** Direction is consistent (B better on prevalence and
  reinfection) but magnitudes need the ensemble + multiple seeds.
- **CT only**; NG/TV extinct in draw 773.

## Next

Reinfection from undertreated concurrent partners is the binding
constraint, which is addressable. Follow-up experiments (ladders, 1 draw
for shape, ensemble later):
1. **PN intensity ladder** — scale PN coverage upward (×1…×N, raising the
   attendance cap) to map the dose-response of reinfection/prevalence.
2. **EPT in the POC arm** — treat all *notified* partners without requiring
   attendance (attend→1.0); tests whether bypassing the attendance leak
   helps (expected modest given the regular-partner coverage gap).
3. **Condoms/counselling for the diagnosed** — a new mechanism reducing
   the cured index's reinfection from still-untreated concurrent partners;
   laddered by coverage.

## Files

- `run.py` — both arms, chain reconstruction, source attribution.
- `tracer.py` — `STIChainTracer` (per-step tx outcomes + monkey-patched
  `set_prognoses` source log with at-transmission FSW/client category).
- `figures.py` → `figures/fig1_ct_chain_flow_{A,B}.png`,
  `fig2_arm_comparison.png`, `fig3_source_attribution.png`.
- `outputs/` — `arm_comparison.csv`, `chain_tree_{A,B}.json`,
  `chains_{A,B}.csv`, `source_breakdown_*.csv`, raw event logs.
- Model change: `pn.py` gained an **opt-in** `trace_events` dyad log
  (default off; no behaviour/RNG change).
