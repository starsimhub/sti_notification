# Exp 02 — Full recalibration on Fix C corrected baseline

**Date:** 2026-06-10.

**Question.** Run the full two-phase LHS pipeline against the
[Fix C corrected model](https://github.com/starsimhub/sti_notification/pull/5)
to produce a new robust posterior ensemble suitable for PN-scenario
decision analysis.

**Result.** **169-draw robust ensemble produced (target 200, hit
84%).** HIV calibration *improved* slightly — HIV+/HIV− trep ratio
band pass rate 90% → 94%, HIV whole-pop median in UNAIDS band. But
**the structural ceiling on syph absolute prevalence reasserted
itself under the multi-target filter**: the 32% nontrep+ improvement
seen on the [exp 01 sustained subset](../01_coverage_check_fixc/SUMMARY.md)
(8.6% unconstrained) was calibrated away (12.7% on the robust
ensemble). Same picture as `archive/calibration-2026-06`'s exp 40.

## Headline scorecard

| metric | old cal (exp 40 ensemble) | exp 01 sustained | exp 02 robust ensemble | ZIMPHIA |
|---|---|---|---|---|
| trep_f_2016 | 0.212 | 0.206 | **0.235** | 0.027 |
| nontrep_f_2016 | 0.126 | 0.086 | **0.127** | 0.008 |
| fsw_prev_2019 | 0.611 | 0.595 | **0.670** | target 0.20–0.40 |
| HIV whole-pop 2010-2020 | (in band) | covered | **0.127 median** | UNAIDS ~0.11–0.13 |
| HIV ratio in band [3.0, 6.0] | 90% | — | **94%** | — |

## Pipeline numbers

- Phase 1: **2000 LHS draws** × 1 seed, ~45 min wall on 60 workers.
- Phase 1 yield: 976 sustained (49% — vs old cal's 35% at 5000 draws,
  Fix C is more stable), 333 candidates passing sustained AND
  n_pass ≥ 5 of 9 targets.
- Phase 2: 333 candidates × 3 seeds = 999 sims, ~23 min wall.
- Phase 2 yield: **169 robust draws** (sustained 3/3 AND mean
  n_pass ≥ 4 of 9 targets).
- Total wall: ~1.1h. New ensemble parquet + draws CSV in
  `outputs/`.

## Per-target pass rates on the robust ensemble (n=169)

| target | band | pass rate |
|---|---|---|
| HIV+/HIV− trep ratio | [3.0, 6.0] | **94%** ✅ |
| HIV whole-pop 2010-2020 mean | [0.09, 0.13] | 53% |
| FSW prev 2019 | [0.20, 0.40] | **1%** ❌ (structural) |
| syph trep_f 2016 | [0.05, 0.10] | 0% (ceiling) |
| syph nontrep_f 2016 | [0.01, 0.05] | 0% (ceiling) |

## Observations

1. **HIV calibration is the win.** Whole-pop 2010-2020 median 12.7%
   (UNAIDS ~11–13%); HIV+/HIV− trep ratio 94% pass on the [3.0, 6.0]
   band (up from 90% on the old calibration). The corrected
   syndromic baseline didn't disrupt HIV; if anything, the slightly
   different transmission environment improved the coupling fit.

2. **Syph absolute prev structural ceiling is confirmed under a
   second, structurally-different baseline.** Old calibration used
   the `gud` product (stage-specific, 0.9 primary / 0.2 secondary);
   Fix C uses two channels (`syndromic_gud` 0.8 universal on ulcer
   eligibility + `syndromic_rash` 0.1 on rash eligibility). Despite
   the structural difference, the minimum-sustaining FoI lands at
   essentially the same equilibrium prev band:
   - Old cal trep_f: 0.212 → exp 02: 0.235 (~10% drift, still 7–9×
     ZIMPHIA)
   - Old cal nontrep_f: 0.126 → exp 02: 0.127 (identical)

3. **The exp 01 sustained-median improvement (8.6% nontrep+) did
   not survive calibration.** Reason: exp 01's median was an
   unconstrained sustained-subset median. Exp 02's robust filter
   adds the HIV-coupling + stage-shares + primary/secondary band
   requirements, which trade off against the lower-nontrep+ region.
   The calibrator picks draws that maximise multi-target satisfaction,
   landing back at the ceiling.

4. **FSW pass rate dropped to 1%** (vs old calibration's 0%). Still
   essentially zero — FSW prev is wedged above the [0.20, 0.40]
   target band on virtually every robust draw, same as before.

5. **Higher sustainability rate (49% vs 35% in old calibration).**
   Fix C is structurally more stable — the broader ulcer-channel
   presumptive treatment makes extinction less likely. This is a
   modest engineering win even if equilibrium prev didn't shift.

## Diagnosis: why didn't Fix C close the gap?

The hope from exp 01 was that the corrected syndromic baseline
(adding presumptive treatment of non-syph GUD presenters → some
latent treatment) would pull active syph prev down. The sustained-
subset median did show that signal. But under calibration:

- The calibrator's goal is to maximise n_pass across all 9 targets.
- HIV-coupling + stage-share targets are easier to hit at higher
  transmission (where the model has enough syph circulating to
  satisfy primary/secondary share constraints).
- Lower-syph-prev draws often had degenerate stage distributions
  (too few primaries, too many late latents) → lower n_pass → not
  selected.

Net: same equilibrium prev, slightly improved HIV story. The model
has a real structural ceiling on syph absolute prev that no
calibration trade-off resolves.

## Acceptance

**Use this ensemble for downstream PN scenario analysis.** Same
caveats as old calibration:

- HIV calibration is the manuscript headline (now slightly stronger).
- Syph absolute prevalence is documented as a structural ceiling
  (now confirmed under two distinct syndromic baselines).
- PN scenarios use relative-effect contrasts; absolute-prev claims
  about Zimbabwe syph are out of scope.

The corrected syndromic baseline (Fix C) is still the right model —
it represents real-world Zimbabwe syndromic management accurately,
even if equilibrium prev under the prior matches the old calibration.

## Next

1. **Exp 03 — publication figures** from this 169-draw ensemble (port
   `calibration/artifacts/scripts/extract_summary.py` + `plot_figures.py`).
2. **Update `calibration/` docs on a release branch** — replace
   `calibration/artifacts/` with the new ensemble, refresh
   `calibration_summary.md` + `methodology.md` with Fix C as the
   active baseline, remove the "superseded" warning from
   `calibration/README.md`. PR to main.
3. **Return to `scenarios/zimbabwe`** branch for PN-scenario design
   on this new baseline.

## Artifacts

- `outputs/phase1_priors.csv` — 2000 LHS draws × 19 priors
- `outputs/phase1_results.jsonl` — per-draw single-seed Phase 1 results
- `outputs/phase1_selection.json` — counts: 2000 ok, 976 sustained, 333 candidates
- `outputs/phase2_candidates.csv` — 333 priors entering Phase 2
- `outputs/phase2_results.jsonl` — per-(draw, seed) Phase 2 results
- `outputs/ensemble_summary.csv` — per-draw seed means + pass flags
- `outputs/draws_used.csv` — 169 robust draws (the publishable ensemble)
