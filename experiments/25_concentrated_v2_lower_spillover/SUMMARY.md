# Exp 25 — Concentrated v2: thinned bridge over-corrected

**Date:** 2026-06-07.

**Question.** Can three targeted bridge-thinning moves
(`prop_f0` 0.55→0.85, `m1_conc` 0.20→0.05, `client_shares`
0.20→0.15) drop spillover from FSW to general population without
losing the FSW pool dynamics from exp 24?

**Result.** **Over-correction — whole epidemic extinguishes by 2019.**
3-seed mean:

| Target | Value | Range | Status |
|---|---|---|---|
| FSW prev 2019 | 0.000 | [0.20, 0.40] | MISS — extinct |
| nontrep_f 2016 | 0.004 | [0.004, 0.016] | "PASS" but on the way down |
| trep_f 2016 | 0.013 | [0.027, 0.05] | MISS but close |
| Primary share plateau | 0.00 | [0.50, 0.65] | n/a (no transmission) |
| Secondary share plateau | 0.00 | [0.25, 0.40] | n/a |
| Sustained to 2040 | 0 | new_inf > 0 | MISS |

## Observations

1. **The trajectory passed through the data band on its way to
   extinction.** nontrep_f at 2016 = 0.4%, trep_f = 1.3% — both
   very close to ZIMPHIA targets — but the epidemic was already
   collapsing. The right configuration is somewhere between exp 24
   (FSW=0.40, nontrep_f=0.15) and this one.

2. **`client_shares` 0.20 → 0.15 was the killer.** Clients are the
   only source of new FSW infections; cutting them 25% pushed FSW R₀
   below 1 and the pool washed out by 2019. The two "below-FSW"
   knobs (`prop_f0` up, `m1_conc` down) on their own would likely
   have preserved FSW dynamics — but we'll know after exp 26.

3. **Asymmetric bridge framing.** A concentrated syph epidemic
   requires two structurally distinct bridges:
   - **Above FSW** = `client_shares`. Need WIDE so clients keep
     reinfecting FSW.
   - **Below FSW** = `m1_conc` + `prop_f0`. Need NARROW so clients
     don't spread to the bulk of general F.

   v2 cut both. Should have only cut below.

## Acceptance

The result is informative even though it failed: it confirms the
asymmetric-bridge framing and points at `client_shares` as the
load-bearing FSW R₀ knob. The two below-FSW knobs can be tested
separately.

## Next

[Opened — see `../26_m1_conc_sweep/`] Sweep `m1_conc` at the v3 base
config (prop_f0=0.85, client_shares=0.20 reverted to exp 24's level)
to find the sweet spot. m1_conc values: [0.05, 0.08, 0.10, 0.12,
0.15, 0.20], 3 seeds each = 18 sims, parallelized.

## Artifacts

- `outputs/results.json` — per-seed + mean summary
- `outputs/stage_shares.csv` — by-year shares (mostly zero past 2019)
- `outputs/series.pkl` — time series per seed
- `run.py` — same driver pattern as exp 24, three config diffs
