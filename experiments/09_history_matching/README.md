# Exp 09 — History matching: wave 1

**Question.** Can history matching narrow the 8-parameter prior to a
NROY region consistent with all calibration targets?

**Motivation.** Exp 08 confirmed coverage passes with the pruned
8-parameter set. Method selection identified HM + trajectory selection
as the appropriate approach (decision-analysis aim, 8 parameters,
~24s/sim, simulation-only likelihood).

**Parameters (8).**
1. `hiv.beta_m2f` (0.005–0.05, linear)
2. `syph.beta_m2f` (0.10–0.35, log → bounds in log space)
3. `ng.beta_m2f` (0.02–0.30, log)
4. `ct.beta_m2f` (0.02–0.30, log)
5. `tv.beta_m2f` (0.02–0.60, log)
6. `structuredsexual.prop_f0` (0.55–0.90, linear)
7. `structuredsexual.m1_conc` (0.05–0.30, linear)
8. `structuredsexual.dur_sw` (2–15, linear)

**Targets.** Summary statistics from simulation outputs compared to data:
- HIV mean prevalence 2000–2010 (data: ~0.116, std ~0.015)
- HIV mean prevalence 2010–2020 (data: ~0.092, std ~0.010)
- NG mean prevalence 2005–2015 (data: ~0.020, std ~0.003)
- CT prevalence F 25-30 (data: 0.12, std ~0.02)
- TV mean prevalence 2005–2015 (data: ~0.111, std ~0.015)
- Syph prevalence F at 2016 (ZIMPHIA: 0.010, std ~0.003)
- Syph prevalence M at 2016 (ZIMPHIA: 0.006, std ~0.002)
- Syph seroprevalence F at 2016 (ZIMPHIA: 0.030, std ~0.005)
- Syph seroprevalence M at 2016 (ZIMPHIA: 0.024, std ~0.005)
- Syph ANC prevalence mean 2000–2015 (BMJ: ~0.020, std ~0.005)
- Syph prev | HIV+ at 2016 (ZIMPHIA: 0.029, std ~0.008)
- Syph prev | HIV- at 2016 (ZIMPHIA: 0.004, std ~0.002)

Standard deviations reflect both data uncertainty and expected
stochastic model noise. Deliberately generous to avoid over-constraining
in early waves.

**Plan.** Bayes linear emulator, LHS sampling, 1000 samples/wave,
implausibility threshold 3.0, auto feature selection, up to 8 waves.
10k agents per simulation.

**Success criteria.** NROY converges within 5–8 waves. Emulator R² > 0.8
for selected features. NROY region is non-empty and contains parameter
sets that produce plausible trajectories for all targets simultaneously.
