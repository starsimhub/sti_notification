# Exp 11 — coverage check on Starsim 4

**Question.** On the Starsim 4 prereleases, can the model reach each of exp 10's 16 targets under its priors (exp 07's plus `hiv.rel_death`)? Can it reach them jointly within each pathogen?

**Why.** It's a new model in several ways:
- **Versions:** starsim 4.0.0rc6, plus stisim `v4` with `SimpleBV` (#618) and condoms (#619).
- **Demography:** AIDS deaths removed from background mortality, and migration on.
- **Targets:**
  - HIV deaths, prevalence and infections from 2000.
  - STICH prevalence in young women.
  - NG and TV prevalence compared among all adults.

At the same betas, v4 also transmits about 1.6–2× more than v3, so exp 07–09's in-band ranges don't carry over.

**Method.**
- All 500 draws of the LHS (seed 47, 10 priors), 1 seed each, 10k agents, 1985–2026.
- `run.py` calls exp 10's `main()` with its output directory redirected.
- `plot.py` shows the trajectories against the data and target bands, and each target against its own parameters.
- Env `stinotif4`.

**Pass criteria.**
- Each target band overlaps the 5–95% prior-predictive range.
- Within each pathogen, some draws reach all of that pathogen's targets at once:
  - HIV: prevalence, infections and deaths;
  - NG: prevalence, young-women prevalence and incidence;
  - CT and TV: their prevalences.
- Note any parameter piled against a prior edge.

**Run** (from the repo root):
```bash
N_WORKERS=150 python experiments/11_2026-11-25_v4_coverage/run.py
python experiments/11_2026-11-25_v4_coverage/plot.py
```
