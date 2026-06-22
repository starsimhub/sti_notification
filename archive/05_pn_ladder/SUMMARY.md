# Exp 05 — PN intensity ladder (+ EPT) — SUMMARY

**Scope.** POC arm, draw 773, 1 seed, CT, window 2030–2034. PN coverage
multipliers ×0/×1/×2/×3/×5/×8 (notify+attend on baseline edge rates,
attend cap 0.99) plus an EPT rung (notify ×5, attend→1.0).

## Result

| rung | CT prev (window) | CT incidence | cohort reinf/100 | mean partners notified | PN attending |
|---|---|---|---|---|---|
| ×0 | 0.203 | 11.44M | 0.59 | 0.00 | 0 |
| ×1 | 0.198 | 11.33M | 0.55 | 0.18 | 0.41M |
| ×2 | 0.191 | 11.40M | 0.57 | 0.38 | 1.53M |
| ×3 | 0.180 | 11.47M | 0.56 | 0.58 | 2.92M |
| ×5 | 0.147 | 11.80M | 0.71 | 0.98 | 6.93M |
| ×8 | 0.132 | 11.59M | 0.66 | 1.12 | 8.35M |
| EPT | 0.146 | 11.85M | 0.66 | 0.98 | 7.07M |

See `figures/fig1_pn_ladder.png`.

## Observations

1. **CT prevalence keeps falling with PN coverage — no early plateau.**
   ×0→×8 drops prevalence 0.203→0.132 (−35% relative). The exp-04
   "modest" effect was just ×3 sitting low on the curve. Scaling PN works,
   but is expensive: ×8 ≈ 20× the PN attendance volume of ×1 for the extra
   reduction. Prevalence tracks `mean partners notified per index` (0→1.1
   of ~1.5 concurrent) — i.e. it improves as concurrent-partner coverage
   approaches completeness, consistent with the exp-04 mechanism.

2. **Incidence is flat (~11.5M) and cohort reinfection does not fall.**
   PN+treatment shortens infectious *duration* (↓ point prevalence) but
   does not reduce new-infection *events*. The reinfection churn persists
   regardless of PN intensity — pointing to a re-acquisition lever
   (condoms, exp 06) as the thing that could move incidence/reinfection
   where PN cannot.

3. **EPT ≈ ×5** (prev 0.146 vs 0.147; reinfection 0.66 vs 0.71). Removing
   the attendance requirement adds essentially nothing, because at ×5
   attendance is already ~0.95. **Notification coverage, not attendance,
   is the binding leak** — EPT is not worth pursuing here (matches the
   prior expectation).

## Caveats

- **1 draw, 1 seed.** The prevalence curve is a clean monotone signal;
  the cohort reinfection rate is noisy (n=100/1 seed) and non-monotone —
  read it qualitatively (it doesn't fall), not point-by-point. Magnitudes
  need the ensemble + seeds.
- **CT only**, draw 773 (NG/TV extinct).

## Next

Prevalence responds to PN but incidence/reinfection don't — so test the
re-acquisition lever: **exp 06 condoms/counselling ladder** from the same
POC + baseline-PN base, for a like-for-like comparison of which lever
moves CT (and especially CT incidence) more.
