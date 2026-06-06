# Exp 17 — History matching against detectable_prevalence targets

**Question.** With the patched stisim that exposes `detectable_prevalence`
and exp 16's verdict that the model is compatible with the active-syph
target after the observability fix, can history matching converge to
an NROY that brackets all the non-coinfection targets while keeping
the model dynamics defensible?

**Motivation.** Exp 16's prior predictive coverage check showed 9/100
draws bracket `syph_detectable_f_2016` at the data target — the first
time in this project that's been true on the active-syph indicator.
The bracket band is thin enough that HM will be required to find the
NROY; a manual posterior won't surface the structure. See
[`../16_coverage_detectable/SUMMARY.md`](../16_coverage_detectable/SUMMARY.md)
for the coverage diagnostic and the WHO Fig 7 framing.

This is the calibration-grade run that supersedes exp 09: same method,
same 8-parameter space, but against the corrected target mapping and
the patched stisim natural history.

**Plan.** Direct mirror of exp 09's HM setup with three deliberate
differences.

1. **Targets (11, not 13).** Syph active prev targets remap from
   `prevalence_f/m` to `detectable_prevalence_f/m`. Other targets
   unchanged. **Two coinfection targets dropped** — `syph_prev_hivpos_2016`
   and `syph_prev_hivneg_2016` — because the `coinfection_stats`
   analyzer in stisim still uses `syph.infected` (counts the
   invisible late-latent reservoir) and would emit artifact-driven
   implausibility scores that pull NROY into the wrong region. To
   be added back via a separate stisim patch + exp 18 wave-extension
   later.

2. **Restart from wave 1, not carry-over from exp 09.** The stisim
   patch (`feat/syph-detectable-state`, commit 24bdf58) introduces an
   extra RNG draw in `set_latent_prognoses` (the `time_to_undetectable`
   draw), shifting the entire random-number sequence. Same seed
   produces different outcomes. Exp 09's wave-1 NROY is not transferable
   under the patched model.

3. **`time_to_undetectable` fixed at the stisim default** (lognormal
   median ~5 yrs, wide). Not opened as a calibration parameter for
   this pass — keep the search space at the established 8 dimensions
   so HM has its best shot at converging. If the NROY turns out
   indefensible on the late-latent reservoir size (e.g. invisible
   reservoir too small or too large vs what the seroprev/anc targets
   imply), open `time_to_undetectable` in a follow-up. Expert input
   on the prior is pending — Monday email at repo root.

**Configuration.**

- 8 parameters (`priors.py`, unchanged): 5 disease betas, 2 network
  parameters, FSW duration.
- 11 targets (above).
- 1000 samples per wave, 10k agents, 1985–2025, up to 8 waves.
- Same emulator + implausibility settings as exp 09.
- 24 workers (memory budget per exp 13's verdict; exp 09 ran with
  more, but tightening is the only safe assumption against the
  patched model).
- Estimated wall-clock: ~30 min per wave (1000 sims × ~28 s ÷ 24
  workers) × 8 waves = ~4 hr total. Resumable per wave via the
  `history_matching` package's checkpoint mechanism.

**Success criteria.**

- **Primary:** NROY at wave 8 (or earlier convergence) contains a
  population of draws that bracket all 11 targets within ~2 widened
  standard deviations.
- **Secondary:** Posterior emulator R² for syph targets is comparable
  to or better than exp 09 (which struggled on syph at R² = 0.18–0.25
  due to the bifurcation it was actually picking up on `prevalence_f`).
  Now that the model can produce the data on `detectable_f`, the
  emulator should fit cleanly — ideally R² > 0.5 for syph after a
  few waves. If R² stays low, the emulator is failing for a different
  reason (insufficient training points in the bracket band, or
  remaining bimodality structure even on detectable).
- **Diagnostic:** Final NROY's invisible-reservoir distribution
  (prevalence_f − detectable_prevalence_f) — sanity check that the
  posterior parameter sets are producing reasonable late-latent
  reservoir sizes, not just satisfying the active target by accident.

**What this experiment does NOT address.**

- Coinfection targets — deferred to exp 18 after `coinfection_stats`
  is patched.
- Treatment-side `detectable` clearing — the WHO Fig 7 mechanism
  where treated early-stage cases drop non-trep titre. Material once
  ANC serology coverage gets high, less material pre-2010s. Deferred.
- `time_to_undetectable` priors — flagged for expert input.
- Decision analysis — exp 19+ once a usable posterior exists.
