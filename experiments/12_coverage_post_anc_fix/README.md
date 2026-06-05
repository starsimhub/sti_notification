# Exp 12 — Coverage check: post-ANC serology fix

**Question.** Does syphilis still sustain and bracket the data after
switching the ANC screen from GUD (ulcer exam, ~5% latent sensitivity)
to era-gated serology (RPR then dual RDT, ~90% latent sensitivity)?

Exp 08 had 55/100 draws sustaining syphilis with the old GUD-based ANC
test. The serology fix (commit dc951f0) dramatically increases ANC
detection → treatment throughput for latent syphilis, which could
push more draws to extinction.

**Changes from exp 08.**
- `interventions.py`: ANC screen now uses RPR (1980–2012) and dual RDT
  (2012+) instead of GUD. Time-varying coverage ramp 20%→95%.
- `data/syph_dx.csv`: added `rpr` product row.
- No prior changes — same 8-parameter set.

**Plan.** 100 prior draws, 10k agents, 1985–2025. Same priors as exp 08.

**Success criteria.** Syphilis targets remain bracketable (some draws
reach ZIMPHIA prevalence/seroprevalence data). If sustainability drops
below ~20/100, the syphilis beta prior may need widening to compensate
for the increased treatment pressure.
