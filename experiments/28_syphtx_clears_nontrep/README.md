# Exp 28 — SyphTx clears non-trep after early-stage treatment

**Date opened:** 2026-06-07.

**Question.** With the stisim bug fixed — `SyphTx.change_states`
now sets `ti_nontrep_end` to 6-12 months post-treatment for agents
treated in primary, secondary, or early latent stages — how much
does `nontrep_f` drop at exp 24's hand-picked configuration?

**Why now.** Exp 27 ruled out parameter-only fixes to the model's
~13.5% nontrep_f at the only sustaining β. Inspection of the SyphTx
code revealed a structural bug: **agents treated during primary,
secondary, or early-latent never have `ti_nontrep_end` set**, so
they remain `nontrep=True` for life despite being biologically
cured. Real biology (WHO 2021 fig 7, confirmed by Robyn): RPR
titres drop 4-fold within ~6 months of adequate early-stage
treatment, with most patients becoming RPR-negative within 6-12
months. Late-latent treatment does NOT reliably clear non-trep.

The fix is a 5-line stisim patch on
`feat/syph-detectable-state`:

```python
# Identify early-stage treated agents BEFORE clearing stage flags
early_stage_mask = d.primary[treat_succ] | d.secondary[treat_succ] | d.early[treat_succ]
early_stage_treated = treat_succ[early_stage_mask]
# ... (existing state clearing) ...
nontrep_treated = early_stage_treated[d.nontrep[early_stage_treated]]
if len(nontrep_treated) > 0:
    months = self.pars.nontrep_revert_months.rvs(nontrep_treated)
    steps = np.maximum(1, np.round(months / (12 * d.t.dt_year)).astype(int))
    d.ti_nontrep_end[nontrep_treated] = d.ti + steps
```

`nontrep_revert_months` is a new `ss.uniform(low=6, high=12)`
Dist parameter on SyphTx (CRN-safe).

See [`../27_beta_sweep/SUMMARY.md`](../27_beta_sweep/SUMMARY.md)
for the diagnosis that motivated this and
[[project-syph-calibration-state]] for project goals + targets.

**Plan.**

Re-run exp 24's hand-pick verbatim — same priors, same network
knobs, same boosted care-seeking CSV, same defensible ANC ramp.
The ONLY difference is the SyphTx patch. Three seeds (matching
exp 24's 101/102/103). Diagnostics: full summary metrics +
stage shares + time series.

**Expected effects.**

| Metric | Exp 24 | Expected change |
|---|---|---|
| FSW prev 2019 | 0.397 | unchanged (~0.40) — the patch doesn't affect transmission |
| nontrep_f 2016 | 0.135 | substantial drop (target [0.01, 0.03]) |
| trep_f 2016 | 0.237 | unchanged (~0.24) — `ever_exposed` is not cleared by SyphTx |
| Primary stage share | 63% | unchanged |
| Secondary stage share | 35% | unchanged |
| Sustained to 2040 | yes | unchanged |

**Success criteria.**

Loose targets from [[project-syph-calibration-state]]:
- FSW prev 2019 ∈ [0.20, 0.40]
- nontrep_f 2016 ∈ [0.01, 0.03]
- trep_f 2016 ∈ [0.05, 0.10]
- Primary share ∈ [0.50, 0.65]
- Secondary share ∈ [0.25, 0.40]
- Sustained to 2040

A **win** = all loose targets pass.
A **partial win** = nontrep_f drops meaningfully (>50%) but doesn't
quite land in band; document and decide whether to keep iterating
or accept as the calibration baseline.
A **null result** = nontrep_f barely moves; would indicate the
SyphTx bug wasn't the dominant inflator (would be surprising
given the diagnosis).

**Decision branches.**

- **Win** → open exp 29 = tight LHS coverage check (~50 draws over
  narrow ranges around this config) for HM input. Calibration done.
- **Partial win** → assess whether the gap is interesting (e.g.
  nontrep_f drops to 0.05 — close to upper loose bound) and either
  declare done or test one more knob.
- **Null** → diagnose why; might mean trep_f is the limiting
  ratio (if trep_f stays at 24% and nontrep_f only drops to ~12%,
  the trep:nontrep ratio improves but absolute trep is still 5×
  data — that's a separate fix).

**What this experiment does NOT do.**

- Does not change priors, network, or care-seeking.
- Does not run HM.
- Does not add the `p_nontrep_persists` (Remco's "75% of untreated
  syph never sero-revert") — separate fix if needed; this one is
  only about the post-treatment cure.
