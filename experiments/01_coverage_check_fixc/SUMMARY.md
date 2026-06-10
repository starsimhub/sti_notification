# Exp 01 — Coverage check on corrected baseline (Fix C)

**Date:** 2026-06-10.

**Question.** Does the 19-parameter prior in [`priors.py`](../../priors.py)
cover the Zimbabwe data — UNAIDS HIV, ZIMPHIA 2015–16 syphilis, and
NG/CT/TV surveillance — under the corrected two-channel syph
syndromic dx baseline ([PR #5](https://github.com/starsimhub/sti_notification/pull/5))?
Prior predictive on 50 LHS draws (1 seed each).

**Result.** **Coverage fails on syph absolute prevalence.** When the
prior predictive bands include all 50 draws (including those where
syph extincts), ZIMPHIA's 2.7% trep+ and 0.8% nontrep+ appear inside
the 5–95% band trivially — but only because the lower CI is pulled
to 0 by the 28 extinction draws. On the **sustained-only subset**
(22/50 = 44% of draws), the 5–95% band on trep+ at 2016 is
**[11.7%, 25.0%]** vs ZIMPHIA's 2.7%, and the nontrep+ band is
[4.6%, 12.9%] vs ZIMPHIA's 0.8%. The structural ceiling we documented
in the old calibration is **not** an artifact of the wrong syndromic
baseline; Fix C narrows the gap only marginally.

![Syph coverage on sustained subset — ZIMPHIA points outside band](figures/fig1_syph_coverage_sustained.png)

## Headline coverage numbers (sustained-only, n=22)

| target | data | sustained median | sustained 5–95% | covered? |
|---|---|---|---|---|
| syph trep+ 15–64 2016 | 0.027 | 0.206 | [0.117, 0.250] | ❌ |
| syph nontrep+ 15–64 2016 | 0.008 | 0.086 | [0.046, 0.129] | ❌ |
| syph FSW 2019 | 0.20–0.40 | 0.595 | [0.330, 0.739] | ❌ (barely overlaps) |
| HIV whole-pop 2010 | ~0.13 | 0.101 | [0.036, 0.147] | ✅ |
| HIV whole-pop 2020 | ~0.11 | 0.094 | [0.018, 0.134] | ✅ |
| HIV 15-49 2016 | 0.159 | 0.147 | [0.035, 0.220] | ✅ |
| NG, CT, TV | — | — | — | ✅ all covered |

## Fix C vs old calibration on sustained-only

| metric | old calibration ensemble median | Fix C sustained median | direction |
|---|---|---|---|
| syph trep+ 2016 | 0.212 | 0.206 | essentially unchanged |
| syph nontrep+ 2016 | 0.126 | 0.086 | slight improvement (~30%) |
| syph FSW 2019 | 0.611 | 0.595 | essentially unchanged |
| HIV whole-pop 2010 | 0.125 | 0.101 | slight shift down |

The HIV calibration win from `archive/calibration-2026-06` carries
across. The syph absolute prev structural ceiling **does not break**
under Fix C. Same picture as exp 40: 5–10× ZIMPHIA on sustained
draws.

## Observations

1. **Initial "covered" verdict was wrong.** First-pass quantiles over
   all 50 draws included extinction trajectories at lower-CI=0, which
   trivially "covered" any low data point. On the sustained-only
   subset the bands tighten dramatically and the gap to ZIMPHIA
   becomes visible.

2. **Extinction rate is 56%** (28/50 draws extinct over 2030-2040).
   Same stochastic bifurcation as before; recalibration's
   sustainability filter still mandatory.

3. **Fix C improves nontrep+ slightly, trep+ negligibly.** The
   structural reshaping of the syndromic channel did what it should
   — secondary syph (rash) treatment dropped, ulcer presumptive
   treatment broadened — but the net effect on equilibrium prev is
   ~30% reduction on nontrep+ and ~3% on trep+. Not enough to reach
   ZIMPHIA.

4. **HIV calibration story unchanged.** Whole-pop and 15-49
   predictives both cover the data; the HIV-syph coupling levers
   should remain identifiable.

5. **FSW band [33%, 74%] barely overlaps the [20%, 40%] target.**
   Even sustained-and-low draws produce FSW prev that runs hot.
   Network-only knobs are unlikely to close this fully.

## Acceptance

**Coverage does not pass for syph absolute prev.** Three paths
forward, in order of pragmatism:

1. **Accept the ceiling and recalibrate anyway.** Reach the same
   manuscript framing as before: HIV calibration is the headline,
   syph results are relative-effect contrasts on the same draws.
   The structural ceiling is documented honestly as a model
   limitation. Cost: ~28h compute. Risk: same outcome as
   `archive/calibration-2026-06`.

2. **Widen the prior on syph transmission** (`syph.beta_m2f` lower
   bound, possibly add `syph.dur_inf` or `syph.p_symp_care` as
   calibration parameters) to try to find a sustained-and-low region.
   The old calibration explored 19 params across ~17k sims without
   finding it; widening may not help, but it's the cheapest next
   experiment — repeat the 50-draw coverage check with a wider prior
   (~4 min compute) before committing to a full recalibration.

3. **Further structural changes.** Possible levers: tighter natural
   history (longer asymptomatic latent? shorter primary?), more
   aggressive ANC ramp, additional baseline treatment paths. Bigger
   model work; uncertain payoff.

## Next

Two options — researcher decision:

1. **Exp 02 = path (2): widen the syph prior and re-run the coverage
   check.** Cheap (~4 min wall), tells us whether there's any room
   in the prior at all.
2. **Exp 02 = path (1): full recalibration on Fix C as-is.** Accept
   the ceiling, get the new ensemble, write manuscript with the
   limitation. ~28h wall.

Recommendation: do (2) first as a cheap diagnostic before committing
to (1)'s 28h. If (2) reveals nothing new, run (1) confident the
ceiling is genuinely structural.

## Artifacts

- `outputs/priors.csv` — 50 LHS draws × 19 priors
- `outputs/time_series.parquet` — raw per-(draw, year) time series
- `outputs/ensemble_ts_quantiles.parquet` — ALL-draw quantiles (misleading on syph due to extinctions)
- `outputs/sustained_draws.csv` — the 22 draw_idxs that sustain (mean syph new_inf 2030–2040 > 0)
- `outputs/sustained_ts_quantiles.parquet` — sustained-only quantiles
- `figures/fig1_syph_coverage.png`, `fig2_hiv_coverage.png`, `fig3_sti_coverage.png` — all-draw plots (kept for transparency about the initial misread)
- `figures/fig1_syph_coverage_sustained.png`, `fig2_hiv_coverage_sustained.png`, `fig3_sti_coverage_sustained.png` — sustained-only (the honest coverage view)
