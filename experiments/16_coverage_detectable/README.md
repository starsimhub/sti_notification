# Exp 16 — Coverage check with detectable_prevalence target mapping

**Question.** With the patched stisim that exposes `detectable_prevalence`
— mapping the model's observability layer to what a dual non-treponemal +
treponemal RDT (ZIMPHIA) would actually detect — does the existing 8-parameter
prior bracket the ZIMPHIA targets when those targets are compared to the
*right* model output?

**Motivation.** Three findings from exp 13 / 14 / 15 / scratch tests:

1. Exp 15 showed background case imports collapse the bifurcation onto the
   hot branch, not near data: every non-zero rate produced ~100% draws at
   17–30% prevalence_f. We concluded the model was structurally incompatible
   with the data target.
2. Per-stage diagnostic ([SUMMARY of scratch tests, this session]) revealed
   the hot branch's 20% `prevalence_f` is almost entirely **late latent**
   accumulation: active disease (primary + secondary) is only ~0.3%, early
   latent ~0.3%, and the rest is a stuck late-latent reservoir that grew
   from 30 years of post-1985 burn-through.
3. Reading the WHO 2021 STI guidelines (Fig 7) confirmed that the
   non-treponemal arm of a dual RDT (what ZIMPHIA measures as "active
   syphilis prevalence") **does not detect most late-latent agents** —
   non-trep titre decays below threshold within ~years of late-latent
   onset. The previous calibration was comparing a model output that
   counts the invisible reservoir to a survey number that doesn't.

The stisim patch (`feat/syph-detectable-state`, commit 24bdf58) adds a
`detectable` agent state and `detectable_prevalence` result that models
this observability layer separately from the biology. Late-latent agents
transition to non-detectable on a per-agent timescale drawn from a
`time_to_undetectable` distribution (default `lognorm_ex(5y, 5y)`, wide).
Reactivation from late latent re-sets detectable=True (titre climbs).
Treatment-side handling is deferred — see SUMMARY's caveats once written.

**Plan.** A prior predictive coverage check, not a calibration run.

1. 100 prior draws (same 8-parameter prior as exp 12), 10k agents, 1985–2025.
2. Extract the existing 13-target set BUT with the syph_prev_f/m target mapping
   changed from `prevalence_f/m` to `detectable_prevalence_f/m`. All other
   targets unchanged (seroprev still maps to `serological_prevalence`, ANC
   targets and coinfection metrics described below).
3. Plot coverage against data for each target.
4. Cross-tabulate: for the hot-branch draws (those that previously read
   ~20% on `prevalence_f`), what does their `detectable_prevalence_f`
   look like? Specifically does it land in the 0.5–3% range that brackets
   the ZIMPHIA 1.0% target?
5. Diagnostic per-draw breakdown: `prevalence_f` − `detectable_prevalence_f`
   = the invisible-to-survey reservoir. Plot the distribution across draws.

**Known caveats this exp will not address (deferred to later):**

- **Coinfection targets (`syph_prev_hivpos_2016`, `syph_prev_hivneg_2016`)
  still use `syph.infected`**, not `syph.detectable`. The coinfection
  analyzer is in stisim and computing the detectable-restricted version
  requires a separate edit. For this exp, we keep the existing analyzer
  and flag the inconsistency. If coverage on the active targets passes,
  the coinfection analyzer is the next stisim PR.
- **ANC targets** currently map to `pregnant_prevalence` and
  `detected_pregnant_prevalence`. The latter applies a fixed
  `anc_detection=0.8` multiplier to a prevalence that counts all infected.
  Conceptually ANC screening would now use the detectable mask among
  pregnant. Same kind of follow-up edit. For now use the existing
  results.
- **Treatment-side detectable clearing** is not implemented. Under the
  current patch, an agent treated in primary/secondary stays detectable
  for the remainder of their natural history. In reality treatment of
  early stages drops non-trep titre. This will under-count clearance
  events — i.e. `detectable_prevalence` will run slightly high vs reality
  in scenarios with significant early-stage treatment coverage. For
  pre-2010s Zimbabwe with limited syph testing this is small;
  post-2010s ANC serology rollout it grows. Deferred to a follow-up
  patch.
- **`time_to_undetectable` distribution is wide and ungrounded** —
  Robyn following up Monday with expert input. For this coverage check
  we use the default lognormal(5y, 5y).

**Success criteria.**

- **Primary:** At least some prior draws land in (0.5–3%) on
  `detectable_prevalence_f` at 2016. If the entire prior cloud sits
  above 3% or below 0.5%, the detectable-state mechanism alone hasn't
  fixed the mismatch and we need to dig further.
- **Secondary:** The (prevalence_f − detectable_prevalence_f) gap is
  large on draws where exp 13/15 read ~20% on prevalence_f — confirms
  the invisible-reservoir interpretation.
- **Subsidiary:** Non-syph targets (HIV, NG, CT, TV) remain bracketed.
  We're not touching their machinery but the RNG shift could
  redistribute draws unfavourably.

If primary passes, we open exp 17 to redo HM against the corrected
target. If primary fails on the upper side (most draws above 3%
detectable), `time_to_undetectable` may need to be a shorter distribution
than the default — wait for expert input before re-running. If primary
fails on the lower side (most draws below 0.5%), the model has a
deeper problem the patched observability layer can't solve.
