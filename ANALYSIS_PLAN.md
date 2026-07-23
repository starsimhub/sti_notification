# sti_notification — analysis plan

**Project**: Health impact of demand-generation strategies (general outreach + partner notification) on STI **undertreatment**, complementing the prior `syph_dx_zim` overtreatment work.

**Diseases modeled (7)**: HIV, syphilis, GUD (placeholder), NG, CT, TV, BV.
**Endpoints reported for**: syph, NG, CT, TV. HIV and BV stay in the model as co-infection / VDS drivers but are not scenario outcomes.
**Settings**: Zimbabwe (active); Kenya + South Africa deferred.
**Deliverable**: ~July 2026.

---

## Research questions

1. How much does partner-notification (PN) coverage change **incidence** and **prevalence** of curable STIs (syph, NG, CT, TV)?
2. How much does increased symptomatic care-seeking (outreach) shift the same endpoints, and how much does it move **undertreatment** and **test yield**?
3. What are the **threshold** levels of PN reach and care-seeking needed for meaningful impact on incidence and prevalence?
4. Does POC (etiological) diagnostics reduce **overtreatment** and **unnecessary partner notification**, and improve **test yield**, relative to syndromic SOC?

## Scope decisions (settled)

| Question | Decision |
|----|----|
| Repo | `sti_notification` on `main` (scenario factorial merged 2026-06-26 via PR #7) |
| Geographies | Zimbabwe only for July deliverable; KE + ZA deferred |
| Diseases | All 7 from day 1 (HIV + syph + GUDP + NG/CT/TV + BV) |
| Endpoints | Incidence, prevalence, overtreatment, undertreatment, test yield, unnecessary PN — per disease (syph / NG / CT / TV). |
| PN mechanism | Edge-stratified `PartnerNotification` from `pn.py`; notify-vs-attend split by edge type and partner sex |
| Care-seeking lever | Scalar `care_seek_mult` on NG/CT/TV `p_symp_care` (`make_sim(care_seek_mult=…)`); syph held at baseline |
| Bundled prevention | `CondomCounseling` (interventions.py): coverage of the diagnosed enrolled in a `rel_sus`-reduction window for ng/ct/tv |
| Diagnostic accuracy | SOC syndromic (`SyndromicManagement` via VDS/UDS) vs POC etiological panel; selected by `poc=` flag in `make_testing` |

## Current state (2026-06-26)

**Calibration baseline:** exp 06 (`experiments/06_2026-06-24_kseed_calibration/`). 500-draw LHS × K=5 sim-averaging, single-phase, continuous weighted goodness-of-fit. Top-30 ensemble used. Draws live at `experiments/06_2026-06-24_kseed_calibration/outputs/draws_used.csv` (the default `DRAWS_CSV` in `run_scenarios.py`). Stisim base: `fix/ng-tx` (off rc1.5.8). Supersedes exp 04 (two-phase LHS + binary sustainability filter); see `CLAUDE.md` for the full lineage.

**First full scenario run completed 2026-06-26.** 65 cells × 5 draws × K=5 seeds = 1625 sims, ~2.5h wall on 80 workers. Outputs in `results/`. K=5 paired seeds (`seed = draw_idx*1000 + sub_idx`) match exp 06's calibration so SOC reproduces the calibration's K=5 mean exactly. Layering / epi / yield figures landed in `figures/` (see `plot_layering*.py`, `plot_epi.py`, `plot_validation*.py`).

## Scenario design

### Wiring scenarios off the calibrated ensemble

Scenarios run through the single root `run_scenarios.py` (not per-experiment
folders — only calibrations live under `experiments/`). The driver:

1. **Loads draws from the current calibration baseline**:
   `experiments/06_2026-06-24_kseed_calibration/outputs/draws_used.csv`
   (override with the `DRAWS` env var). **Not**
   `calibration/artifacts/draws_used.csv` — that's the older baseline,
   historical only.
2. **Applies each draw via `_pipeline.set_pars_local`** (in
   `calibration/artifacts/scripts/_pipeline.py`). `sti.Sim` stores
   modules in lists not dicts, so dict-style overrides silently miss;
   `set_pars_local` matches by `mod.name`. Do not reimplement this.
3. **Layers the three levers on the loaded draw** (not in place of it).
   Care-seeking and PN intensity diverge only at the intervention year
   (2027): SOC and POC-baseline runs share `pn_pars=PN_INTENSITY['baseline']`
   and `care_seek_mult=1.0` pre-2027, then the `CareSeekScaler` and
   `PNIntensitySwitch` interventions (in `interventions.py`) toggle the
   active rates from 2027 onwards. Bundled prevention adds a
   `CondomCounseling(**BUNDLED_PREVENTION[b], start=2027)` intervention.
   The draw sets calibrated transmission / network parameters; the
   levers sit on top.
4. **Ladders are defined once in `scenarios.py`** (`CARE_SEEKING`,
   `PN_INTENSITY`, `BUNDLED_PREVENTION`), so cells stay declarative and
   the same levels feed any figure.

### Wiring check before the full run

Before running at full ensemble size, run the **smoke check** end-to-end
(`SMOKE=1 N_WORKERS=30 python run_scenarios.py`): 5 cells (SOC, POC-plain, and
each lever at its highest setting), 5 draws, K=5 seeds = 125 sims (~50 min on
30 workers, 10k agents). Its purpose is catching silent failures — draws not
loaded, a lever not applied, cells not differing pre-2027 — not reproducing
headline results. Verify each lever moves prevalence / incidence /
treatment-precision in the right direction from 2027 onwards.

### Levers (the three ladders in `scenarios.py`)
- **Symptomatic care-seeking** — `CARE_SEEKING`: scalar `care_seek_mult` on NG/CT/TV `p_symp_care`, applied at 2027 by `CareSeekScaler`. Scales the VDS pathway only.
- **Partner notification** — `PN_INTENSITY`: dict of notify-rate and attendance-rate spec (edge type × partner sex), applied at 2027 by `PNIntensitySwitch`.
- **Bundled prevention** — `BUNDLED_PREVENTION`: `CondomCounseling` (`rel_sus` reduction) — coverage of the diagnosed enrolled (eff + duration fixed; coverage is the axis).

Each ladder has 4 rungs (baseline/low/moderate/high). Diagnostic accuracy (SOC vs POC) is the framing arm, set by the `poc=` flag.

### Scenario design — full factorial (ZW)
- `SOC` — syndromic standard of care, all levers baseline (the reference).
- `POC × CARE_SEEKING × PN_INTENSITY × BUNDLED_PREVENTION` = 4 × 4 × 4 = 64 cells; the (baseline, baseline, none) corner is "POC plain". **65 distinct cells total**.

Each cell propagated through the top-30 exp 06 ensemble (first full run used 5 draws × K=5 seeds; the headline run will use more draws). The factorial surfaces both main effects (each lever's dose-response) and interactions. First full run (5 draws × K=5): 1625 sims, ~2.5h wall on 80 workers.

### Endpoints
Six endpoints, each reported per disease (syph, NG, CT, TV) as scenario contrasts across the POC × CARE_SEEKING × PN_INTENSITY × BUNDLED_PREVENTION factorial plus SOC.

| Endpoint | Definition | Source |
|----|----|----|
| Incidence | Annual new infections | per-disease `new_infections` (subsumes "onward syph transmission averted": the same quantity for syph) |
| Prevalence | Point-in-time infected fraction | per-disease `prevalence` (+ `symptomatic_prevalence` for syph) |
| Overtreatment | Treatments delivered to true-negative individuals | per-treatment `new_treated_unnecessary` (already tracked) |
| Undertreatment | Infected individuals who did not receive care in the year | prevalence − treated positives; per-disease |
| Test yield | True positives per test administered on the offered panel | `tests_administered` + `new_treated` (POC vs SOC contrast) |
| Unnecessary PN | Notifications triggered by a true-negative index case (restricted to NG / CT / syph — BV-only tx not counted as waste) | sex-stratified PN funnel in `pn.py` (`new_index_total_{f,m}`, `new_index_no_sti_{f,m}`) |

## Manuscript framing (locked in from the calibration)

- **Endpoints read as scenario contrasts** — POC vs SOC and lever dose-response — with the top-N ensemble × K=5 supplying the propagation envelope. Absolute levels come along for the ride, but the story is the deltas across the factorial.
- **Syph, NG, CT, TV** ensemble means sit on or near their calibration targets in the current baseline (exp 06 top ensemble); envelope width across the ensemble is the honest uncertainty band.

## Recalibration triggers

Recalibrate if any of:
- Any change to `model.py` that affects calibrated endpoints (new disease, new connector, changed natural-history defaults). **Currently triggered: the BV-in-VDS edit (`SimpleBV` + `bv_care`) changed the VDS care-seeking pathway after the active ensemble was fit.**
- A stisim minor version bump (1.6.x) — parameter scales are not transferable across minor versions per `calibration/recalibration_guide.md`.
- Refreshed ZIMPHIA / UNAIDS data that shifts target bands beyond the 80% CI.

See `calibration/recalibration_guide.md` for the full when-to-recalibrate criteria.
