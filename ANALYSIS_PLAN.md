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
| PN mechanism | Edge-stratified `PartnerNotification` from `pn.py`; notify-vs-attend split by edge type and partner sex |
| Care-seeking lever | Scalar `care_seek_mult` on NG/CT/TV `p_symp_care` (`make_sim(care_seek_mult=…)`); syph held at baseline |
| Bundled prevention | `CondomCounseling` (interventions.py): coverage of the diagnosed enrolled in a `rel_sus`-reduction window for ng/ct/tv |
| Diagnostic accuracy | SOC syndromic (`SyndromicManagement` via VDS/UDS) vs POC etiological panel; selected by `poc=` flag in `make_testing` |

## Current state (2026-06-22)

**Calibration baseline on stisim rc1.5.7.** See `experiments/02_2026-06-22_calibration_per_disease_sustain/SUMMARY.md` (the active baseline, 26 draws under a per-disease sustainability filter); the earlier 53-draw syph-only-filter ensemble is superseded but its time-series + age × sex snapshot parquets remain as a historical reference under `experiments/01_2026-06-15_calibration_rc1.5.7/outputs/`. Draws used: `experiments/02_2026-06-22_calibration_per_disease_sustain/outputs/draws_used.csv`. 17 priors. **This baseline predates the BV-in-VDS edit (`SimpleBV` + `bv_care`); re-fire before the headline factorial.**

**Scenarios scaffolding.** `interventions.py` has `SyndromicPN`, `POCPN`, `make_testing`, `make_pn`, and `CondomCounseling` ready; `model.py` builds the 7-disease sim with `FetalHealth` wired via `custom=`. The three scenario ladders live in `scenarios.py`. The factorial is driven by the single root `run_scenarios.py` (smoke-tested) — see *Wiring scenarios off the calibrated ensemble* below.

## Scenario design

### Wiring scenarios off the calibrated ensemble

Scenarios run through the single root `run_scenarios.py` (not per-experiment
folders — only calibrations live under `experiments/`). The driver:

1. **Loads draws from the current calibration baseline**:
   `experiments/02_2026-06-22_calibration_per_disease_sustain/outputs/draws_used.csv`
   (override with the `DRAWS` env var after recalibration). **Not**
   `calibration/artifacts/draws_used.csv` — that's the older baseline,
   historical only.
2. **Applies each draw via `_pipeline.set_pars_local`** (in
   `calibration/artifacts/scripts/_pipeline.py`). `sti.Sim` stores
   modules in lists not dicts, so dict-style overrides silently miss;
   `set_pars_local` matches by `mod.name`. Do not reimplement this.
3. **Layers the three levers on the loaded draw** (not in place of it):
   `care_seek_mult=CARE_SEEKING[c]` and `pn_pars=PN_INTENSITY[p]` into
   `make_sim`, and a `CondomCounseling(**BUNDLED_PREVENTION[b])` when
   bundled prevention is on. The draw sets calibrated transmission /
   network parameters; the levers sit on top.
4. **Ladders are defined once in `scenarios.py`** (`CARE_SEEKING`,
   `PN_INTENSITY`, `BUNDLED_PREVENTION`), so cells stay declarative and
   the same levels feed any figure.

### Wiring check before the full run

Before running at full ensemble size, run the **smoke check** end-to-end
(`SMOKE=1 python run_scenarios.py`): 6 spanning cells (SOC, POC-plain, and each
lever at its maximum, plus all-max), 1 draw, 2k agents. Its purpose is catching
silent failures — draws not loaded, a lever not applied, cells not differing —
not reproducing headline results. Verify each lever moves prevalence /
incidence / treatment-precision in the right direction.

### Levers (the three ladders in `scenarios.py`)
- **Symptomatic care-seeking** — `CARE_SEEKING`: scalar `care_seek_mult` on NG/CT/TV `p_symp_care`, baseline 1.0 → 2.2 (female care-seeking saturates near 2×). Scales the VDS pathway only.
- **Partner notification** — `PN_INTENSITY`: single axis co-varying notify + attend rates (edge type × partner sex) from SOC baseline to a plausible maximum.
- **Bundled prevention** — `BUNDLED_PREVENTION`: coverage of the diagnosed enrolled in a `CondomCounseling` `rel_sus`-reduction window (eff + duration fixed; coverage is the axis).

Each ladder has 5 rungs (baseline/none → maximum). Diagnostic accuracy (SOC vs POC) is the framing arm, set by the `poc=` flag.

### Scenario design — full factorial (ZW)
- `SOC` — syndromic standard of care, all levers baseline (the reference).
- `POC × CARE_SEEKING × PN_INTENSITY × BUNDLED_PREVENTION` = 5 × 5 × 5 = 125 cells; the (baseline, baseline, none) corner is "POC plain". 126 distinct cells total.

Each cell propagated through the 26-draw ensemble. The factorial surfaces both main effects (each lever's dose-response) and interactions (e.g. does PN add to bundled prevention, or substitute?). Single-lever response and the "better dx → less unnecessary PN" contrast both fall out as slices. Full run ≈ 126 × 26 ≈ 3300 sims (~95 min on 60 cores at 1 seed).

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

1. **Review the `CARE_SEEKING` levels** in `scenarios.py` (new ladder; values provisional).
2. **Recalibrate (BV-aware).** The active baseline predates the `SimpleBV` + `bv_care` VDS edit. Re-fire calibration, then point `run_scenarios.py` at the new ensemble via the `DRAWS` env var (or update the default path).
3. **Run the factorial.** `conda run -n starsim env N_SEEDS=1 N_WORKERS=60 python run_scenarios.py` (smoke check first). Output → `results/scenarios.jsonl`.
4. **Add the unnecessary-notification metric.** Tag attendees whose true-negative status across all four PN diseases (ng/ct/tv/syph) means the notification was unwarranted.
5. **DALY post-processing.** Apply standard weights to incident cases, deaths, and APO/ABO outputs.
6. **Endpoint reporting.** Figures in `figures/`: main-effect dose-response per lever, interaction slices, and the dx contrast (POC vs SOC: treatment precision, unnecessary PN). Report with ensemble quantile envelopes.

## Recalibration triggers

Recalibrate if any of:
- Any change to `model.py` that affects calibrated endpoints (new disease, new connector, changed natural-history defaults). **Currently triggered: the BV-in-VDS edit (`SimpleBV` + `bv_care`) changed the VDS care-seeking pathway after the active ensemble was fit.**
- A stisim minor version bump (1.6.x) — parameter scales are not transferable across minor versions per `calibration/recalibration_guide.md`.
- Refreshed ZIMPHIA / UNAIDS data that shifts target bands beyond the 80% CI.

See `calibration/recalibration_guide.md` for the full when-to-recalibrate criteria.
