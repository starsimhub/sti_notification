# sti_notification — analysis plan

**Project**: Health impact of demand-generation strategies (general outreach + partner notification) on STI **undertreatment**, complementing the prior `syph_dx_zim` overtreatment work.

**Diseases (7)**: HIV, syphilis, GUD (placeholder), NG, CT, TV, BV.
**Settings**: Zimbabwe (active); Kenya + South Africa deferred.
**Deliverable**: ~July 2026.

---

## Research questions

1. How much do partner-notification (PN) coverage levels change health outcomes (APO/ABO, DALYs, infections averted)?
2. How much does increased general care-seeking (outreach) change the same outcomes?
3. What are the **threshold** levels of PN reach and outreach needed for meaningful impact?
4. Does better diagnostic accuracy reduce **unnecessary** partner notification (and thus PN-associated harms, e.g. GBV risk)?

## Scope decisions (settled)

| Question | Decision |
|----|----|
| Repo | `sti_notification` on `scenarios/zimbabwe` branch |
| Geographies | Zimbabwe only for July deliverable; KE + ZA deferred |
| Diseases | All 7 from day 1 (HIV + syph + GUDP + NG/CT/TV + BV) |
| Health endpoints | APO + ABO + DALYs (primary); HIV infections, onward syph transmission, GUD-mediated HIV (secondary) |
| PN mechanism | Edge-stratified `PartnerNotification` from `pn.py` on the `PriorPartners` recall network; notify-vs-attend split for current and previous partners; recall window as a parameter |
| Care-seeking lever | Vary `p_symp_care` (NG/CT/TV same value; syph is per-stage `p_symp_primary`/`p_symp_secondary`) |
| Diagnostic accuracy | SOC syndromic (`SyndromicManagement` via VDS/UDS) vs POC etiological panel; selected by `poc=` flag in `make_testing` |

## Current state (2026-06-15)

**Calibration baseline on stisim rc1.5.7.** See `experiments/04_calibration_per_disease_sustain/SUMMARY.md` (the active baseline, 26 draws under a per-disease sustainability filter); exp 03's 53-draw syph-only-filter ensemble is superseded but its time-series + age × sex snapshot parquets remain as a historical reference under `experiments/03_calibration_rc1.5.7/outputs/`. Draws used: `experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv`. 17 priors.

**Scenarios scaffolding.** `interventions.py` has `SyndromicPN`, `POCPN`, `FSWOutreach`, `make_testing`, `make_pn` ready. `model.py` builds the 7-disease sim with `FetalHealth` wired via `custom=` for APO/ABO accounting. Each scenario run lives in its own `experiments/NN_<slug>/run.py` — see *Wiring scenarios off the calibrated ensemble* below for the contract.

## Scenario design

### Wiring scenarios off the calibrated ensemble

Every scenario run lives in its own `experiments/NN_<slug>/run.py`,
following the pattern from `experiments/01_poc_pilot_3arm/run.py`.
The `run_sweeps.py` / `plot_sweeps.py` files at the repo root were
pre-experiment-folder scaffolding and have been removed; do not
resurrect that shape. Each scenario `run.py` must:

1. **Load draws from the current calibration baseline**:
   `experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv`. **Not**
   `calibration/artifacts/draws_used.csv` — that's the older 2026-06-10
   baseline, kept for historical comparison only.
2. **Apply each draw via `_pipeline.set_pars_local`** (in
   `calibration/artifacts/scripts/_pipeline.py`). `sti.Sim` stores
   modules in lists not dicts, so dict-style parameter overrides
   silently miss; `set_pars_local` iterates and matches by `mod.name`.
   Do not reimplement this.
3. **Use edge-stratified PN via `pn_rates`**:
   `pn.pn_rates({'stable': p_stable, 'casual': p_casual, ...})`.
   Flat-scalar Bernoullis ignore the edge-type structure of the
   network and don't match the calibrated PN dynamics. Edge-rate
   dicts are baseline-multiplied per `BASELINE_NOTIFY` /
   `BASELINE_ATTEND` constants (see exp 01's `run.py` for the pattern).
4. **Vary scenario kwargs around the loaded draw**, not in place of
   it. The draw sets calibrated transmission / network / care-seeking
   parameters; the scenario kwargs (PN coverage, care-seeking
   multiplier, `poc=`) layer on top.

### Wiring check before each scenario sweep

Before running any new scenario at full ensemble size, run a
**1-draw × 3-seed wiring check** end-to-end:

- Pick one draw (e.g. the median-n_pass row of `draws_used.csv`).
- Compare a no-PN cell vs a high-PN cell.
- Verify that notification counts move in the right direction and
  order of magnitude.

This is a wiring check, not a science check. It does not need to
reproduce headline results from prior experiments (which were
calibrated against a different baseline). Its purpose is catching
silent failures: draws not actually loaded, PN rates not actually
applied, scenarios not differing as expected.

### Levers (constructed from `interventions.py` per scenario)
- **PN coverage**: 4 levels (none / low / med / high). Each level is a dict of edge-stratified rates passed via `pn_rates` — `{'stable': p_stable, 'casual': p_casual}` for notify and `{'stable': {'f': p, 'm': p}, ...}` for attend (see exp 01's `BASELINE_NOTIFY` / `BASELINE_ATTEND` and the multiplier pattern).
- **PN recall window**: `dur_recall` ∈ {3 mo, 6 mo, 12 mo} on `PriorPartners`.
- **Care-seeking intensity**: multiplier on `p_symp_care` ∈ {1.0×, 1.25×, 1.5×, 2.0×}. Same multiplier for NG/CT/TV; separate setting for syphilis primary/secondary.
- **Diagnostic accuracy**: SOC syndromic vs POC etiological (`poc=` flag).

### Scenario grid (ZW)
Three orthogonal sweeps over the calibrated ensemble:

1. **PN sweep** — fix dx=SOC, care-seeking=baseline, recall=6mo; vary PN coverage 4 ways.
2. **Outreach sweep** — fix dx=SOC, PN=med, recall=6mo; vary care-seeking 4 ways.
3. **Dx × PN interaction** — 2 dx × 4 PN coverage = 8 cells, fixed care-seeking baseline. This is where the "better dx → less unnecessary PN" story lands.

Each cell propagated through the 26-draw ensemble in `experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv`. Apply seeds via the standard 3-seed pattern from `experiments/01_poc_pilot_3arm/run.py`.

### Endpoints
| Endpoint | Source | Notes |
|----|----|----|
| HIV new infections | `hiv.results.new_infections` | Stratify by sex |
| Syph symptomatic prevalence | `syph.results.symptomatic_prevalence` | Primary + secondary stages |
| Syph onward transmission averted | Counterfactual diff | Recorded at module level |
| Adverse pregnancy outcomes | `FetalHealth` connector (wired) | Syph + HIV |
| Adverse birth outcomes | Same | Stillbirth, preterm, LBW |
| DALYs | Post-hoc on incident cases + deaths + APOs | Standard weights |
| Treatments delivered | per-treatment `new_treated` | Already tracked |
| Unnecessary treatments | per-treatment `new_treated_unnecessary` | Already tracked; key metric for dx arm |
| Notifications sent / partners attending | `pn.results.new_notified`, `new_attending` | Already tracked on `PartnerNotification` |
| Unnecessary notifications | Notifications to true-negative partners | New metric needed for the dx arm |

## Manuscript framing (locked in from the calibration)

- **HIV calibrates cleanly** — ensemble median 11.4% whole-pop 2010–20 in the UNAIDS band. HIV is the headline.
- **Syph absolute prev overshoots ZIMPHIA** (medians trep 25.9%, nontrep 12.9% vs targets 2.7%, 0.8%) — this is a model structural ceiling, documented honestly. Syph results are **relative-effect contrasts** under PN scenarios, not absolute calibration.
- **Relative-effect endpoints** (primary/secondary syph share, HIV+/HIV− trep ratio, FSW prev) land in their bands.

## Next concrete steps (ordered)

1. **Wire scenarios off the 26-draw ensemble.** Following *Wiring scenarios off the calibrated ensemble* above, build a single new `experiments/NN_<slug>/run.py` (modeled on `experiments/01_poc_pilot_3arm/run.py`) that loads `experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv`, applies each draw via `_pipeline.set_pars_local`, and uses edge-stratified `pn_rates`. Run the 1-draw wiring check first.
2. **Add the unnecessary-notification metric.** Tag attendees whose true-negative status across all four PN diseases (ng/ct/tv/syph) means the notification was unwarranted.
3. **DALY post-processing.** Apply standard weights to incident cases, deaths, and APO/ABO outputs.
4. **Run the three sweeps.** Open a new experiment folder per sweep (e.g. `experiments/04_pn_sweep/`, `experiments/05_outreach_sweep/`, `experiments/06_dx_pn_interaction/`) — or one combined folder if the storage cost stays reasonable. Let the `calib:project-workflow` skill decide.
5. **Endpoint reporting.** For each sweep, report the endpoints above with ensemble quantile envelopes. Threshold curves (PN coverage vs APO/ABO averted; care-seeking intensity vs HIV infections averted) and the dx × PN interaction plot are the headline figures.

## Recalibration triggers

Recalibrate if any of:
- Any change to `model.py` that affects calibrated endpoints (new disease, new connector, changed natural-history defaults).
- A stisim minor version bump (1.6.x) — parameter scales are not transferable across minor versions per `calibration/recalibration_guide.md`.
- Refreshed ZIMPHIA / UNAIDS data that shifts target bands beyond the 80% CI.

See `calibration/recalibration_guide.md` for the full when-to-recalibrate criteria.
