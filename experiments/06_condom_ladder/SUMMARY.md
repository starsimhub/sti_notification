# Exp 06 — condoms/counselling-for-diagnosed ladder — SUMMARY

**Scope.** POC arm + baseline PN (×1, the shared base with exp 05 rung x1),
draw 773, 1 seed, CT, window 2030–2034. `cond.CondomCounseling`
(mechanism b: on treatment, `rel_sus ×0.5` for ng/ct/tv for 6 months, with
probability = coverage). Coverage ladder 0 / 0.25 / 0.5 / 0.75 / 1.0.

## Result

| coverage | CT prev (window) | CT incidence | cohort reinf/100 | mean protected |
|---|---|---|---|---|
| 0.00 | 0.198 | 11.33M | 0.55 | 0 |
| 0.25 | 0.192 | 10.96M | 0.55 | 0.14M |
| 0.50 | 0.187 | 10.66M | 0.53 | 0.26M |
| 0.75 | 0.183 | 10.37M | 0.58 | 0.37M |
| 1.00 | 0.181 | 10.25M | 0.51 | 0.47M |

See `figures/fig1_condom_ladder.png` and
`figures/fig2_pn_vs_condom_plane.png`.

## Observation — the two levers are near-orthogonal

Head-to-head from the shared POC+baseline-PN base (exp 05 x1 = exp 06
cov 0):

- **Condoms reduce CT *incidence*** (11.33M → 10.25M, −10% at full
  coverage) and prevalence modestly (0.198 → 0.181, −9%). They prevent
  new-infection *events* by protecting the cured index from re-acquisition.
- **PN scaling (exp 05) reduces CT *prevalence*** hard (0.198 → 0.132 at
  ×8) but leaves **incidence flat** (~11.5M). It shortens infectious
  duration without stopping transmission events.

In the prevalence–incidence plane the PN ladder moves ~straight down while
the condom ladder moves ~left — they act on different parts of the
dynamics. For health-outcome endpoints (incidence-driven APO/DALYs vs
prevalence-driven burden) this means **the two levers are complementary,
not substitutes**; PN alone never touches incidence.

## Caveats

- **1 draw, 1 seed.** Prevalence/incidence curves are clean monotone
  signals; cohort reinfection rate is noise-dominated (read qualitatively).
- **Bounded lever.** Condoms here protect only *treated* agents'
  re-acquisition (ng/ct/tv), 50% effective, 6-month window — so the ~10%
  incidence reduction is a floor for this narrow form, not the ceiling of
  a broader prevention package.
- **CT only**, draw 773 (NG/TV extinct). Mechanism b is acquisition-only
  (`rel_sus`); onward `rel_trans` left to disease dynamics.

## Next

- **Combine the levers** (PN scaling × condom coverage) to test additivity
  — expected to move both axes.
- **Ensemble + seeds** for real effect sizes before any manuscript claim.
- Mechanism **(a)** (condom-use uplift through the network) if a more
  literal condom representation is wanted, and extend `rel_trans` (onward).
- A draw where **NG** circulates, to test whether NG (more concentrated)
  differs from CT.
