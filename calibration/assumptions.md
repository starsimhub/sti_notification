# Assumptions and limitations

What's *fixed*, what we *know we can't do*, and what to *watch for*.
Read this before extending the model or interpreting downstream
results.

## Fixed parameters (not opened for calibration)

| Parameter | Value | Why fixed |
|---|---|---|
| Condom effectiveness | STIsim defaults | Strong literature evidence; not jointly identifiable from prevalence. |
| `p_symp` per disease | STIsim defaults | Symptom-fraction is a clinical property, calibrating it against prevalence introduces a confound. |
| `p_symp_care` | 0.75 | Set deliberately based on Zimbabwe care-seeking surveys; sensitivity would be a separate analysis. |
| Symptomatic care-seeking rates | Per `data/symp_test_prob_concentrated.csv` | Derived from surveillance, not a degree of freedom. |
| ANC syph testing probability ramp | 0.05 → 0.90 over 1990 → 2020 (`ANC_PROBS_REALISTIC`) | Programmatic / policy fact, not biology. Tested sensitivity in exp 22; relaxing it does not recover ZIMPHIA absolute prev. |
| Baseline partner-notification rates | Stable 0.20 / casual 0.10 (`SyndromicPN` defaults) | The ensemble represents *with-baseline-PN* state of the world; scenarios contrast against this. |
| n_agents | 10,000 | Stochastic-extinction floor at this scale; smaller populations bifurcate too easily, larger populations were too slow within the project timeline. |

## Structural limitations of the model

### Syphilis absolute prevalence has a structural ceiling

This is the most important limitation. **The minimum-sustaining force
of infection for endemic syph in this model corresponds to
treponemal+ ≈ 23% and non-treponemal+ ≈ 13% — 9–16× the ZIMPHIA
data.** Four independent structural attempts to drive this down
failed:

- **Observability patch (exp 16, 17).** Mapped to RDT-detectable
  prevalence — closed part of the gap but absolute level still hot.
- **Care-seeking ramp variation (exp 22).** Softened the ANC ramp;
  sustainability gate failed before band was reached.
- **Marital coital-decay mechanism (exp 40).** The mechanism is
  identifiable (`stable_act_decay` median 0.10/yr, `client_marital_act_mult`
  median 0.66) but the calibrator compensates by raising other
  transmission knobs — net change on absolute prev: third decimal.
- **Fix C two-channel syndromic dx (recalibration exp 02, 2026-06-10).**
  Replaced the `gud` product (stage-specific 0.9 primary / 0.2
  secondary) with `syndromic_gud` (0.8 universal) on a broader
  ulcer-eligible pool, and added a weak `syndromic_rash` (0.1)
  channel. Coverage-check sustained-subset showed nontrep+ improving
  by 32% (12.6% → 8.6%) — but the multi-target calibration filter
  on 2000 LHS draws pushed nontrep+ back up to 12.7%. Essentially
  unchanged equilibrium prev under a structurally distinct baseline.

Mechanism (best diagnosis): high-risk → low-risk leakage routes are
large in absolute terms (~24% of all transmissions in exp 38) but
structurally locked in; reducing one route gets compensated by
another. The general-population M↔F engine self-sustains independent
of FSW seeding (32% of plateau transmissions in exp 32). The Fix C
recalibration confirms the ceiling is a property of the model's
transmission structure and treatment-flow geometry, not of any
specific syndromic dx assumption.

**Implication for downstream work.** Frame syph results as
*relative-effect* contrasts (PN scenario A vs B). Do not make absolute
claims about Zimbabwe syph burden.

### FSW prevalence target/result mismatch

The calibration's FSW prevalence target band (0.20–0.40 at 2019) and
the model's `prevalence_sw` result are **not measuring the same
thing**. `prevalence_sw` is `cond_prob(self.infected, fsw)` in
[STIsim's syphilis module](https://github.com/InstituteforDiseaseModeling/stisim/blob/main/stisim/diseases/syphilis.py),
where `self.infected` covers **every disease stage** — exposed,
primary, secondary, early latent, late latent, and tertiary. The
target band almost certainly comes from a survey that uses a
specific test type (treponemal serology, non-treponemal serology,
or active-infection-by-clinical-criteria), each of which counts a
narrower or broader pool of agents.

This mismatch is why the 169-draw ensemble's FSW pass rate is 1%
(against a model median of 0.67 vs target [0.20, 0.40]). The model
result is dominated in equilibrium by late latent + tertiary carriers
who are not actively transmitting and would not test positive on
non-treponemal serology — but the calibration is comparing it to a
band that probably refers to either trep+ or active-disease serology.

**Implication.** Treat the FSW pass rate (1%) as not directly
interpretable. For downstream scenario work, use the right model
result for the FSW target: `sexually_transmissible_prevalence_sw` for
"transmissible at the bedside", or a future `trep_prevalence_sw` /
`nontrep_prevalence_sw` if those are added to STIsim. Identified
2026-06-10 during the Fix C recalibration close-out; not fixed in the
current ensemble.

### Stochastic sustained/decay bifurcation

Even within the final ensemble, draws sit near a sustained/decay
attractor boundary. In the Fix C recalibration: 49% of Phase 1
single-seed draws sustained (vs 35% in the original calibration —
the corrected baseline is more stable but the bifurcation is still
present). The robust subset is hotter than the fragile subset (FSW
median 0.67 vs the [0.20, 0.40] target — though see the FSW target
mismatch caveat above). This is a known property of ABMs at 10k
agents and is not unique to syph or to this calibration.

**Implication.** Results above ~10k agents may behave differently —
larger populations would suppress stochastic extinction and could
shift the basin of attraction. Not tested.

### CT calibration is weak

Model CT prevalence in women 25–29 sits ~2× above surveillance (~25%
median vs ~12% data). The 80% CI brackets the data, so it survives
the ensemble filter, but the median is not a good fit. Cause:
candidate explanations are (a) the CT beta prior was permissive on
the low side, or (b) symptomatic care-seeking parameters drain the CT
pool too fast.

**Implication.** Acceptable for PN scenarios where CT impact is a
secondary outcome. If CT-specific claims become central, run a
targeted CT diagnostic before publishing.

### TV is mostly in band, slightly under post-2020

Model TV runs about 2 pp below surveillance from 2020 onward. Within
80% CI. Not a known structural issue.

## Bounded confidence in the HIV result

- HIV whole-pop and 15–49 medians sit in the UNAIDS / ZIMPHIA bands
  on both denominators.
- HIV incidence is in the right order of magnitude but **declines
  slightly more slowly than UNAIDS post-2015.** The ART roll-out
  ramp baked into the model lags the actual ramp. This is partly
  absorbed by `rel_init_prev` but not fully closed.

**Implication.** Late-period absolute HIV incidence values from the
model are noisier than the prevalence values. Use carefully if
downstream work compares HIV incidence across scenarios in 2020+.

## Known abandoned hypotheses

These are documented here so future researchers don't retrace dead
ends. Full per-experiment context on `archive/calibration-2026-06`
(original cycle) and `archive/recalibration-2026-06-fixc` (Fix C
recalibration cycle).

| Hypothesis | Experiment | Outcome |
|---|---|---|
| Widening the syph beta prior recovers basins of sustained transmission. | 01–05 | Beta is not the bottleneck — network is. |
| Exogenous case imports / FOI floor will prevent extinction without ruining the fit. | 15 | Imports of 1.4% collapsed the bifurcation onto the hot branch (17.7% median). Rejected. |
| Waning immunity drives the early-burnout dynamics. | 16 diagnostic | Observability was the real bottleneck, not waning immunity. |
| `rel_trans_primary = 5` produces a more realistic primary-driven epidemic. | 29 | Fragility: 2/3 seeds collapse. Abandoned. |
| FSW MF-concurrency multiplier seeds the general-population engine. | 33 | Sweep [0.1, 1.0]: zero correlation with non-trep_f outcomes. Hypothesis falsified. |
| Marital coital-decay mechanism breaks the M_client → F_other syph leakage. | 40 | Identifiable but compensated for by other knobs. No effect on absolute prev. |
| Coupled-model approach: pool extinct + sustaining sims to produce average prev in the data band. | 40 (open thought, never implemented) | Not pursued — would require infrastructure outside STIsim. |
| Fix C two-channel syndromic dx (syndromic_gud + syndromic_rash) breaks the ceiling. | recal exp 02 | Improves HIV coupling (90% → 94% pass), improves sustainability (35% → 49%), and unconstrained sustained-subset shows 32% nontrep+ reduction; multi-target calibration filter trades that back. Net effect on equilibrium prev: essentially nil. |

## What no one has answered

Open questions left for future work:

- **Coupled-model / population-mixing approach.** Robyn's idea (exp 40)
  to pool 1 sustaining + 4 extinct sims as a 50k-agent "uber-population"
  whose average prev hits the ~2% data band. Mathematically appealing,
  not yet tested.
- **Is the CT under-calibration a recent regression or always present?**
  Worth comparing exp 36 vs exp 38 CT trajectories to localise.
- **HIV incidence ramp post-2015.** Could a sharper ART roll-out
  parameterisation close the remaining ~10–20% gap to UNAIDS?

These are useful directions but not blockers for the PN decision
analysis.
