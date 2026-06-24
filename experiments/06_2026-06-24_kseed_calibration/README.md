# Exp 06 — single-phase K=5 calibration with weighted GoF + extinction penalty

**Question.** Under the K=5 sim-averaging paradigm (each parameter draw runs
at 5 independent seeds; the 5-seed mean is the unit of signal), what
parameter ensemble best matches the empirical Zimbabwe STI calibration
targets? Replaces exp 04's two-phase LHS + binary sustainability filter
with a single-phase LHS + continuous goodness-of-fit + top-N retention.

**Plan.** Same 17-param prior as exp 04, same LHS seed 45. K=5 seeds per
draw. Each sim extracts the 11 calibration target scalars + a time series
+ age × sex snapshots. Per draw: mean across 5 seeds for every metric.
GoF computed on per-draw means; rank ascending; retain top N.

GoF formula:
```
distance(target_t) = max(0, (lo_t - mean_t) / (hi_t - lo_t), (mean_t - hi_t) / (hi_t - lo_t))
MAE = sum(w_t * distance_t) / sum(w_t)   # weighted mean
extinction_penalty = 100 * |{disease : all K=5 seeds extinct on disease}|
GoF = MAE + extinction_penalty   # lower = better
```

Weights: `{trep_f_2016, nontrep_f_2016, hiv_trep_ratio_2016,
pf_2035_2040_ng, pf_2035_2040_ct} = 2`; `{ni_2030_2040_ng,
ni_2030_2040_ct, ni_2030_2040_tv} = 0.5` (soft tiebreaker — catches
draws that match prevalence by holding people infected too long, even
when prev is in band); all other targets = 1.

Targets (14):
| target | band | from |
|---|---|---|
| hiv_prev_2010_2020 | [11.5, 15.5]% | UNAIDS |
| trep_f_2016 | [2.0, 4.0]% | ZIMPHIA |
| nontrep_f_2016 | [0.5, 1.5]% | ZIMPHIA |
| hiv_trep_ratio_2016 | [3.0, 6.0] | computed |
| fsw_prev_2019 | [40, 70]% | network data |
| primary_share | [45, 65]% | expert opinion |
| secondary_share | [25, 45]% | expert opinion |
| early_lat_share | [5, 25]% | expert opinion |
| pf_2035_2040_ng | [1.0, 2.5]% | sti_data.csv |
| pf_2035_2040_ct | [9, 15]% | sti_data.csv |
| pf_2035_2040_tv | [7, 14]% | sti_data.csv |
| ni_2030_2040_ng | [200, 400]k/yr | sti_data.csv |
| ni_2030_2040_ct | [300, 600]k/yr | sti_data.csv |
| ni_2030_2040_tv | [1100, 2200]k/yr | sti_data.csv |

Stages:
1. **Smoke** (20 draws, same as exp 05 pilot): verify plumbing — GoF
   computation, per-draw averaged time series, age × sex snapshots, raw
   per-sim archive. Match the pilot's per-draw scalar means to confirm
   nothing changed under the new extract.
2. **Compute check** (100 draws, ~75 min wall): confirm extrapolation,
   produce first epi_overview-style figure to see whether the new
   approach gives visually better trajectories.
3. **Full calibration** (500 draws, ~6.25 hr wall): produce the
   exp-06 ensemble.

Stisim pinned to `fix/ng-tx@731bc1d`.

**Success criteria.**
- Smoke: scalar means at the 20 draws match the pilot's per-draw means
  bit-for-bit (same priors, same seeds, same code path for the K=5
  averaging). Time series + snapshot parquets written cleanly.
- Compute check: retention at top-N produces a sensible ensemble. The
  epi_overview-style plot shows model bands that bracket the empirical
  prevalence data more cleanly than exp 04's ensemble does.
- Full calibration: retained ensemble size 50–200 (tunable N). NG-runs-hot
  caveat from exp 04 substantially improved or resolved. Syph absolute
  prev structurally still overshoots but ensemble brackets data within
  the structural-ceiling regime.

**What's saved per stage (in `outputs/`):**
- `priors.csv` — LHS draws
- `results_raw.jsonl` — per-sim raw scalars (archive, not used for analysis)
- `per_draw_means.csv` — K=5 averaged scalars + GoF + retention rank
- `timeseries.parquet` — per-draw averaged year × disease × {prev_f,
  prev_m, new_infections}
- `snapshots.parquet` — per-draw averaged age × sex × disease at
  snapshot years 2016, 2027, 2035, 2040

Out of scope: scenario re-run against the new ensemble (separate task
after exp 06 closes).
