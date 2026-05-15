# Exp 04 — Coverage check: mid-risk concurrency

**Date:** 2026-05-15.

**Question.** Exps 02–03 showed syphilis seeds but crashes to zero despite
high-risk group changes. Does raising mid-risk concurrency (`f1_conc`
0.05→0.15, matching `syph_dx_zim`) sustain syphilis through the data
window? See [`../03_coverage_check_network_fix/SUMMARY.md`](../03_coverage_check_network_fix/SUMMARY.md).

**Result.** Partial improvement. 7/100 draws now sustain syphilis above
0.1% by 2020 (vs 2/100 in exp 03, 1/100 in exp 02), with the best draw
reaching 0.86%. But no draws reach the ~2% data and 93/100 still go
extinct. The HIV-syphilis coinfection connector (`rel_sus_hiv_syph=2.67`)
is already active, so that's not a missing lever.

![Prior predictive coverage check — 100 draws. Some syphilis sustainability but insufficient.](figures/coverage.png)

## Observations

1. **Concurrency helps but doesn't solve.** The decay is visibly slower
   and 7 draws sustain vs 2 before, but the effect is incremental.

2. **`syph.beta_m2f` is the strongest predictor of sustainability.**
   Sustaining draws average 0.16 vs 0.09 for extinct draws. `rel_trans_primary`
   shows no difference (6.7 vs 6.7). Lower `prop_f0` (more women in
   mid/high-risk) also helps.

3. **The `hiv_syph` connector is already present** with `rel_sus_hiv_syph=2.67`
   and `rel_trans_hiv_syph=1.2` (auto-added by STIsim). This amplifier is
   active; adding it was not the missing piece.

4. **The prior is too wide for syphilis beta.** The log-uniform prior on
   `syph.beta_m2f` (0.01–0.35) puts most mass in the low range. The
   `syph_dx_zim` posterior median was 0.17 (5th–95th: 0.15–0.22). A
   tighter or shifted prior would concentrate draws in the sustaining
   region.

5. **NG/CT/TV/HIV unchanged** — all still pass.

## Next

The model can sustain syphilis — 7 draws prove it — but the prior
puts most mass in the extinction region. Two options for exp 05:

- Tighten `syph.beta_m2f` prior to 0.10–0.35 (informed by syph_dx_zim
  posterior) and/or raise `rel_trans_primary` floor from 3 to 5.
- Add `m1_conc` to the default (0.15 matching f1_conc) rather than
  relying on the calibration prior to find it.
