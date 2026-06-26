# Exp 07 — PN × condom combined grid — SUMMARY

**Scope.** POC arm, draw 773, 1 seed, CT, window 2030–2034. 3×3 grid:
PN coverage multiplier {×1, ×3, ×8} × condom-counselling coverage
{0, 0.5, 1.0} (eff 0.5, 6-mo window). 9 cells.

## Result

CT prevalence (2030–34 mean):

| PN \ condom | 0.0 | 0.5 | 1.0 |
|---|---|---|---|
| ×1 | 0.198 | 0.187 | 0.181 |
| ×3 | 0.180 | 0.162 | 0.151 |
| ×8 | 0.132 | 0.121 | **0.115** |

CT incidence (new infections, window, millions):

| PN \ condom | 0.0 | 0.5 | 1.0 |
|---|---|---|---|
| ×1 | 11.33 | 10.66 | 10.25 |
| ×3 | 11.47 | 9.92 | 9.13 |
| ×8 | 11.59 | 8.67 | **7.87** |

See `figures/fig1_pn_x_condom_heatmap.png`.

## Observations

- **Best corner (×8, full condom): prevalence 0.115 (−42% vs base 0.198)
  and incidence 7.87M (−30% vs 11.33M).** Combining gets the lowest of
  *both* axes — PN supplies the prevalence drop, condoms the incidence
  drop.
- **Prevalence reduction ≈ additive.** PN-only −0.066 + condom-only −0.017
  = −0.083; combined −0.083.
- **Incidence reduction is super-additive (synergistic).** PN-only ≈ flat
  (+0.26M), condom-only −1.08M → sum −0.82M; **combined −3.46M**. Condoms
  are ~3.4× more potent at ×8 PN than at ×1.
- **Mechanism of the synergy:** `CondomCounseling` protects *treated*
  agents from re-acquisition. High PN drags far more partners into
  treatment, so it enlarges the pool condoms then protect — PN *feeds*
  the lever condoms act on. The two are not just complementary
  (orthogonal axes) but mutually reinforcing on incidence.

## Caveats

- **1 draw, 1 seed.** Prevalence/incidence grids are clean monotone
  signals; the synergy is a robust qualitative pattern, but magnitudes
  need the ensemble. cohort reinfection (not tabled) stayed noise-dominated.
- **CT only**, draw 773 (NG/TV extinct). Condom lever is the narrow
  acquisition-only form (treated agents, ng/ct/tv, 50%, 6 mo).

## Next

Re-run exps 05–07 across the **~50-draw sustained ensemble** (Robyn
recalibrating ~2026-06-18 to find draws where all critical STIs persist)
for real magnitudes + uncertainty. The code is already parameterised by
`draw_idx`; wrap in the ensemble loop and report quantile envelopes.
