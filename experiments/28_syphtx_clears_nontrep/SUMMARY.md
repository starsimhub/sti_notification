# Exp 28 — SyphTx clears non-trep after early-stage treatment

**Date:** 2026-06-07.

**Question.** With the stisim bug fix to `SyphTx.change_states`
applied (set `ti_nontrep_end` to 6-12 months post-treatment for
agents treated in primary, secondary, or early latent stages), how
much does `nontrep_f` drop at exp 24's hand-picked configuration?

**Result.** **Clean structural improvement of -32% on `nontrep_f`,
everything else identical** (same CRN streams). The bug was real:

| Metric | Exp 24 | Exp 28 | Delta |
|---|---|---|---|
| FSW prev 2019 | 0.397 | 0.397 | 0.000 |
| nontrep_f 2016 | 0.151 | **0.103** | **-0.048 (-32%)** |
| trep_f 2016 | 0.237 | 0.237 | 0.000 |
| Primary share | 63% | 63% | 0 |
| Secondary share | 35% | 35% | 0 |
| Sustained | yes | yes | — |

## Observations

1. **The bug was real and inflating nontrep_f by ~50%.** Before
   the fix, treated agents stayed nontrep+ for life — `ti_nontrep_end`
   was only set when entering late latent, never for early-stage
   treated. After the fix, treated agents become nontrep- within
   6-12 months of treatment, matching WHO 2021 fig 7's "RPR drops
   4-fold within 6 months" guidance.

2. **trep_f did not change** because `ever_exposed` is correctly
   not cleared by SyphTx (trep antibodies persist for life in the
   ever_exposed semantics — though we later refined this with the
   trep BoolState + 80% persistence in subsequent stisim patches).

3. **Other metrics unchanged.** Stage shares, FSW prev,
   sustainability, transmission rates — all identical to exp 24.
   The fix is purely a state-cleanup that should have been there
   from the start; it doesn't touch transmission dynamics.

4. **But still 3-10× the loose ZIMPHIA bands.** nontrep_f drops
   to 10% — still 3× the loose ceiling. The remaining gap is
   driven by active-stage prevalence + late-latent persistence,
   neither of which this fix addresses.

## Acceptance

The fix is a clean, defensible structural improvement (real
biology, no parameter pushing). It alone doesn't close the gap to
the loose target band — see [`../29_rel_trans_primary_5/SUMMARY.md`](../29_rel_trans_primary_5/SUMMARY.md)
for the next attempted lever.

## Next

[Done — see [`../29_rel_trans_primary_5/SUMMARY.md`](../29_rel_trans_primary_5/SUMMARY.md)]
Layer further structural changes: rel_trans_primary as a
calibration knob, dur_early extended to 22-24mo, hand-picked at
rel_trans_primary=5 with 3 seeds.

## Artifacts

- `outputs/results.json` — per-seed + mean
- `outputs/stage_shares.csv` — by-year stage attribution
- `run.py` — single-config driver reusing exp 24 machinery
