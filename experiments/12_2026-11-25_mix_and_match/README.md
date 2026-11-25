# Exp 12 — mix-and-match calibration on Starsim 4

**Question.** Combine per-pathogen parameter sets that each fit their own pathogen in exp 11's screen. Run at K=5 seeds against exp 10's targets (the CT 25–30 target is dropped: CT is fitted to STICH alone). Does that give at least 30 acceptable draws? Are the couplings between pathogens weak enough that the combinations still fit?

**Why.** Each target depends almost only on its own pathogen's parameters (exp 07), so a single LHS rarely lands every pathogen at once.

**Method.**
- **Pools:** from exp 11's 500 × 1-seed screen. For each pathogen, the draws that sustained, with all of that pathogen's targets within their acceptance tolerance:
  - HIV: 15–49, whole-population prevalence and deaths, both decades. Its draws also carry the network parameters.
  - NG: adults, young women, and incidence (within 1.0 band-width).
  - CT: young women.
  - TV: adults and young women.
- **Combinations:** 200, sampling one draw from each pool. With replacement where a pool has fewer than 200.
- **Run:** K=5 seeds, 10k agents, 1985–2030, through exp 10's `main()`, with scoring, acceptance and retention of the top 30 unchanged. Env `stinotif4`.

**Pass criteria.** At least 30 acceptable draws. Acceptance per pathogen comparable to the pools' screen rates, which would show the couplings are weak.

```bash
N_WORKERS=150 python experiments/12_2026-11-25_mix_and_match/run.py
```
