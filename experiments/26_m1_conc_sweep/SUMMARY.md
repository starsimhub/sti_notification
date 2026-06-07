# Exp 26 — m1_conc sweep: no sweet spot, ratio is structural

**Date:** 2026-06-07.

**Question.** At the v3 base config (`prop_f0=0.85`,
`client_shares=0.20`), does some value of `m1_conc` land the
epidemic concentrated-sustained — FSW prev ~30%, nontrep_f ~1%,
sustained?

**Result.** **No sweet spot. Of 18 sims (6 m1_conc × 3 seeds), only
2 sustained to 2040**, both at seed 101, m1_conc ∈ {0.15, 0.20}.
Even those have nontrep_f at the **exp-24 level** (~16%) — `prop_f0`
lifted from 0.55 → 0.85 did NOT reduce spillover when the FSW pool
was active. The ratio FSW:general (model ~2.7) is structural under
this network architecture and isn't sensitive to either knob.

| Sustained config | FSW prev 2019 | nontrep_f 2016 | trep_f 2016 | primary % | sec % |
|---|---|---|---|---|---|
| m1_conc=0.15, seed 101 | 0.38 | 0.158 | 0.249 | 62% | 36% |
| m1_conc=0.20, seed 101 | 0.44 | 0.159 | 0.248 | 65% | 34% |

The other 16 sims either extinguished outright (seed 102 across all
6 values) or visited a 2016 cross-section near 15% nontrep_f and
then crashed toward extinction by 2040.

## Observations

1. **Stochastic extinction dominates at 10k agents.** Seed 102 went
   extinct everywhere; seeds 101 and 103 had divergent fates at the
   same parameters. At this agent count the system sits near a
   bistable boundary and noise alone determines which basin is hit.

2. **prop_f0 redistributes infection but doesn't reduce it.** With
   prop_f0=0.55 (exp 24) the spillover lands in a larger rg1 pool;
   with prop_f0=0.85 (this exp) it lands in a smaller rg1+rg2 pool at
   higher per-capita rate. Total fraction of women non-trep-positive
   ends up the same ~16%.

3. **Stage shares stay right.** Primary 60-65%, secondary 34-36% in
   the sustained runs — confirms (again) that disease natural-history
   isn't the issue.

4. **Decay-through-target pattern recurs.** A run at m1_conc=0.12 had
   2016 cross-section nontrep_f=0.17 but mean prev_f at 2035-40
   = 0.017 (just above the sustainability floor). 2016 looks
   passable but the trajectory is dying. This is the same failure
   mode that motivated [[feedback-calibration-guards]] back in
   exp 21.

5. **The concentration ratio (FSW:gen) is a network-architecture
   property.** Model produces ratio ~2.7 because clients have
   non-trivial stable partnerships with non-FSW women — the
   FSW→client→wife bridge stays wide regardless of m1_conc /
   prop_f0. To shift the ratio, need a structural intervention
   (condom use in client-wife pairs, or shorter stable_dur_pars for
   clients, or behavioural mutual-exclusivity of FSW-only clients).

## Acceptance

The structural diagnosis is now clear: **parameter-only knobs on
the existing network architecture cannot push the model below
~5-7% general nontrep_f** while keeping FSW=30% and sustainability.
A different lever is needed.

## Next

[Opened — see `../27_beta_sweep/`] Sweep `syph.beta_m2f` from 0.08
to 0.20 to find the lowest β that still sustains. If the floor of
nontrep_f at sustainability is 5-7%, that's the model's structural
limit and the choice is whether to (a) accept the loose-target band
as the calibration goal, or (b) open the marital-MF condom-use
lever (Robyn's earlier idea, deferred).

Also: the loose calibration targets are now formalized
([[project-syph-calibration-state]] updated):
- nontrep_f_2016 ∈ [0.01, 0.03] (1-3%)
- trep_f_2016 ∈ [0.05, 0.10] (5-10%)
- FSW prev 2019 ∈ [0.20, 0.40]
- Stage shares primary 50-65%, secondary 25-40%
- Sustained to 2040.

## Artifacts

- `outputs/results.json` — per-seed summary + best m1_conc by hit-count
- `outputs/sweep_summary.csv` — 3-seed mean per m1_conc
- `outputs/series.pkl` — FSW prev, nontrep_f, trep_f, overall prev_f time series
- `run.py` — parallelized sweep driver
