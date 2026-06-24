# Exp 05 pilot SUMMARY — K=5 sim-averaging validation

**Date:** 2026-06-24.

**Question.** Before committing to a full single-phase K=5 recalibration,
verify mutual understanding of the design. 20 LHS draws from the exp 04
prior × K=5 seeds, no filter applied, just look at the per-draw means and
per-seed spreads.

**Result.** Design validated. K=5 averaging recovers the "bimodal-fate"
draws the approach was designed for (some seeds extinct, some sustain →
mean falls in a sensible range). Full-extinction draws (all K=5 seeds dead
on a disease) are cleanly separable. The proposed GoF metric (band-edge
distance + extinction penalty) gives sensible rankings that match
intuition.

## Key findings

1. **The 0%/15%/0%/0%/0% pattern exists in the data.** Draws 12, 13, 17
   (syph) and the TV-extinct draws all show seed-level bimodality on at
   least one disease. Their K=5 means fall close to the empirical bands
   when sustained-seed values are high and extinct-seed values are 0 —
   exactly the recovery mechanism the approach hypothesised.

2. **GoF design locked.** Band-edge distance per target (in band-widths
   from nearest band edge), averaged across 11 targets, weighted
   {trep_f, nontrep_f, hiv_trep_ratio, pf_2035_2040_ng,
   pf_2035_2040_ct} = 2 and others = 1. Extinction penalty +100 per
   disease extinct in all K=5 seeds. Retention by top-N ascending GoF.

3. **trep_F and nontrep_F INCLUDED** despite structural ceiling. The
   K=5 averaging gives bimodal-fate draws a path to in-band means on
   these targets; the rest are penalised by the band-edge distance
   but not catastrophically (no implicit infinity).

4. **NG/CT/TV late-period prev added** (`pf_2035_2040_{ng,ct,tv}`) using
   bands derived from `data/zimbabwe_sti_data.csv`: NG [1.0, 2.5]%,
   CT [9, 15]%, TV [7, 14]%.

5. **Compute estimate.** Pilot ran 100 sims in ~15 min wall (60 workers).
   Per-sim wall ≈ 9 min. Extrapolation: 100 draws × K=5 = 500 sims ≈
   75 min; 500 draws × K=5 = 2,500 sims ≈ 6.25 hr.

6. **Band-edge vs midpoint distance barely differ** for the pilot —
   rankings stable across both metrics because most draws are outside
   most bands (structural ceilings, parameter mismatches). Band-edge
   wins on simplicity.

## Caveats

- No retention applied in the pilot; the GoF analysis is post-hoc on the
  20-draw data.
- NG/CT/TV target bands set heuristically around the `sti_data.csv` 2025+
  values with modest uncertainty buffers. May need tuning if exp 06
  retention is too tight/loose.

## Next

**Exp 06** — implements the locked spec. Starts with a 20-draw plumbing
test to verify the GoF + per-draw-averaged time series + snapshots
infrastructure, then scales to 100 draws (compute check) and 500 draws
(full calibration). Saves per-draw averaged outputs (philosophy: the
5-seed mean is the unit of signal, not the individual sub-sim).
