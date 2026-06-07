# Exp 29 — rel_trans_primary=5 + extended early latent (22-24mo)

**Date opened:** 2026-06-07.

**Question.** With three structural changes layered on exp 28's
config — (a) `rel_trans_primary` lifted from 1 to **5** (Robyn:
"in previous work, we set rel_trans_primary higher, like around 5"),
(b) `dur_early` extended from 12-14 mo to **22-24 mo** (matches
WHO Europe early-latent boundary), and (c) the SyphTx-clears-nontrep
patch from exp 28 — can the model produce concentrated-sustained
syph in the loose target band?

**Why now.** Exp 28 showed that fixing the SyphTx-doesn't-clear-nontrep
bug dropped nontrep_f by 32% (0.151 → 0.103) without touching
transmission dynamics. The remaining gap is in `trep_f` (24% vs
loose target 5-10%) — that's the steady-state cumulative-incidence
implied by the model's annual incidence ~0.5% (vs ZIMPHIA-implied
0.05%). The two new structural changes target that:

- **`rel_trans_primary = 5`**: primary becomes much more
  transmissible per contact, while secondary stays at 1.0 and latent
  decays from 1.0 with half-life 1y. Concentrating transmission in
  primary (~6 weeks) means R₀ is built from short, intense windows
  rather than long latent tails, and lets us potentially calibrate
  to a lower beta_m2f that gives lower overall incidence while
  still sustaining via FSW treat-reinfect cycles.
- **`dur_early = 22-24 mo`**: stisim default was 12-14 mo, but WHO
  Europe uses ≤2y for early latent (Robyn). Mostly affects
  congenital transmission and stratified nontrep stock; minor
  effect on overall sexual transmission shape.

Loose stage-share targets relaxed today
([[feedback-stage-share-check]] updated):
- Primary ~55% (acceptable 45-65%)
- Secondary ~35% (acceptable 25-45%)
- Early latent ~10% (acceptable up to ~15%)
- Late latent: small remainder

**Plan.**

Re-run exp 28's hand-pick verbatim, with **one parameter override**:
`syph.rel_trans_primary = 5`. The `dur_early` change is structural
(in stisim default). Three seeds (101, 102, 103), same diagnostics:
summary metrics + stage shares + time series.

**Expected effects.**

| Metric | Exp 28 | Hypothesis |
|---|---|---|
| FSW prev 2019 | 0.397 | might rise (primary much more transmissible) |
| nontrep_f 2016 | 0.103 | could go either way — depends on whether primary-stage spillover dominates |
| trep_f 2016 | 0.237 | unclear — depends on how fast new infections accumulate vs how many treated |
| Primary stage share | 63% | UP (5× rel_trans concentrates transmission here) |
| Secondary stage share | 35% | DOWN |
| Sustained to 2040 | yes | should still sustain, possibly hotter |

If FSW prev goes too hot (>0.50) but general nontrep stays bounded,
the move is to **reduce beta_m2f to compensate**. If general
nontrep drops into band while FSW prev stays in band, win.

**Success criteria (loose targets).**

- FSW prev 2019 ∈ [0.20, 0.40]
- nontrep_f 2016 ∈ [0.01, 0.03]
- trep_f 2016 ∈ [0.05, 0.10]
- Primary share ∈ [0.45, 0.65]
- Secondary share ∈ [0.25, 0.45]
- Early latent share ≤ 0.15
- Sustained to 2040

**Decision branches.**

- **All targets pass** → open exp 30 = tight LHS coverage check
  around this config for HM input.
- **FSW prev passes but general nontrep too high** → reduce β
  to compensate; iterate.
- **Things look qualitatively right but absolute numbers still
  high** → accept this as the calibration baseline, move to
  decision-analysis phase per the framing in
  [[project-syph-calibration-state]].
- **Extinction** → indicates that the layered changes (rel_trans
  patch + nontrep patch + dur_early extension) put us in a fragile
  basin. Reduce one change, retest.

**What this experiment does NOT do.**

- Does not run HM.
- Does not add `p_nontrep_persists`.
- Does not edit condom CSV.
- Does not change network architecture.
