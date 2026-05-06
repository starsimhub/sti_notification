# sti_notification — analysis plan

**Project**: Health impact of demand-generation strategies (general outreach + partner notification) on STI **undertreatment**, complementing the prior `syph_dx_zim` overtreatment work.

**Diseases (7)**: HIV, syphilis, GUD (placeholder), NG, CT, TV, BV.
**Settings**: Zimbabwe (prelim), then Kenya + South Africa.
**Timeline**: preliminary results in ~2 weeks; full analysis ~July.

---

## Research questions

1. How much do partner-notification (PN) coverage levels change health outcomes (APO/ABO, DALYs, infections averted)?
2. How much does increased general care-seeking (outreach) change the same outcomes?
3. What are the **threshold** levels of PN reach and outreach needed for meaningful impact?
4. Does better diagnostic accuracy reduce **unnecessary** partner notification (and thus PN-associated harms, e.g. GBV risk)?

## Scope decisions (settled)

| Question | Decision |
|----|----|
| Repo | `sti_notification` (existing stub repo, modernized) |
| Geographies | ZW first; KE + ZA next |
| Diseases | All 7 from day 1 (HIV + syph + GUDP + NG/CT/TV + BV) |
| Health endpoints | APO + ABO + DALYs (primary); HIV infections, onward syph transmission, GUD-mediated HIV (secondary) |
| PN mechanism | Use `PriorPartners` network + repo's existing `PartnerNotification` class with notify-vs-attend split for current and previous partners; recall window treated as a parameter |
| Care-seeking lever | Vary `p_symp_care` (NG/CT/TV same value; syph is per-stage `p_symp_primary`/`p_symp_secondary`) |
| Custom PN class | Promote to stisim layer 2 (replace base `PartnerNotification`) |

## Where things live (layer hierarchy)

- **Layer 1 (`starsim`)** — no changes expected.
- **Layer 2 (`stisim`)** — promote the upgraded `PartnerNotification` class (notify×attend, current+previous network split) here. Fix `gud_syph` connector signature and attribute typo (`syphilis` vs `syph`) as a side PR. Fix `hiv_bv` explicit-construction sim-linking bug as a side issue.
- **Layer 3 (`sti_notification`)** — sim assembly, scenario logic, country-specific data, outcome accounting, run scripts, plots.

## Repo state after modernization (this session)

`model.py` (renamed from `vds_model.py`), `hiv_model.py`, `interventions.py` updated for stisim v1.5.5:
- Switched to `sti.Sim` (auto demographics path available, not yet used)
- Dropped `**time_units` everywhere — sim defaults to monthly dt
- `ART/VMMC` use `coverage=` (renamed from `coverage_data=`)
- `BV` (full CST model) replaces `SimpleBV`; BV no longer in syndromic-VDS eligibility (uses internal care-seeking)
- `GUDPlaceholder` instantiated as `name='gudp'` to bypass buggy `gud_syph` auto-connector
- Connectors auto-added by `sti.Sim` (workaround for explicit-construction bug)
- `which='all'` builds all 7 diseases; smoke-tested over 1990–1993, 500 agents (~1.2s)

## Known issues to fix before scenarios

1. **`PartnerNotification` set-and bug** (`interventions.py:337,344`): `successful_m_idx = nw.p1[fp_edge_inds] & m_idx` is wrong — set-and on UID arrays, not the edge intersection that's intended. **Fix when promoting to stisim.**
2. **Syphilis testing not wired**: `make_syph_testing` returns only `SyphTx` for the smoke test. Need `SyphDx` product CSV in `data/` and either a symptomatic test pathway, ANC pathway, or both.
3. **APO/ABO outcome accounting**: not yet implemented. Reuse `FetalHealth` connector from the ANC screening repo for syph-driven adverse pregnancy outcomes; need design for HIV+other STIs.
4. **DALY accounting**: no module yet. Standard approach: post-hoc weights on incident cases, deaths, and APO/ABO, applied during result processing.
5. **`hiv_bv` and `gud_syph` connector bugs**: workarounds in place (auto-add + name='gudp'). Fix upstream in stisim before promotion PR.
6. **Country data**: only ZW data files present (`asfr.csv`, `deaths.csv`, `age_dist_1990.csv`, `condom_use.csv`, `n_art.csv`, `n_vmmc.csv`, `init_prev_*.csv`). Need KE + ZA equivalents.

## Scenario design

### Levers
- **PN coverage**: 4 levels (none / low / med / high) — already structured in `run_pn_scens.py`. Vary both `p_notify` and `p_attends`, separately for `current` and `previous` partners.
- **PN recall window**: `dur_recall` ∈ {3 mo, 6 mo, 12 mo}.
- **Care-seeking intensity**: multiplier on `p_symp_care` ∈ {1.0×, 1.25×, 1.5×, 2.0×}. Same multiplier for NG/CT/TV; separate setting for syphilis primary/secondary.
- **Diagnostic accuracy**: SOC syndromic vs POC etiological (already structured via `poc=` flag). Important for the dx→PN-precision arm.

### Scenario grid (prelim, ZW only)
A 2 × 4 × 3 × 4 grid (192 cells) is too much for prelim. Instead, three orthogonal sweeps:

1. **PN sweep** — fix dx=SOC, care-seeking=baseline, recall=6mo; vary PN coverage 4 ways.
2. **Outreach sweep** — fix dx=SOC, PN=med, recall=6mo; vary care-seeking 4 ways.
3. **Dx × PN interaction** — 2 dx × 4 PN coverage = 8 cells, fixed care-seeking baseline. This is where the "better dx → less unnecessary PN" story lands.

Each cell × 20 stochastic seeds = ~250 sims for the prelim. Fits on a laptop.

### Endpoints
| Endpoint | Source | Notes |
|----|----|----|
| HIV new infections | `hiv.results.new_infections` | Stratify by sex |
| Syph active prevalence | `syph.results.active_prevalence` | |
| Syph onward transmission averted | Counterfactual diff | Need to record at module level |
| Adverse pregnancy outcomes | `FetalHealth` (port from anc_sti_screening) | Syph + HIV |
| Adverse birth outcomes | Same | Stillbirth, preterm, LBW |
| DALYs | Post-hoc on incident cases + deaths + APOs | Standard weights |
| Treatments delivered | per-treatment `new_treated` | Already tracked |
| Unnecessary treatments | per-treatment `new_treated_unnecessary` | Already tracked; key metric for dx arm |
| Notifications sent / partners attending | New on PN class | Need to add results |
| Unnecessary notifications | Notifications to true-negative partners | New metric — the central outcome for the dx arm |

## Phasing

### Phase 0 — completed today (smoke test)
- Modernized for stisim v1.5.5
- All 7 diseases run end-to-end
- ZW data in place; KE/ZA pending

### Phase 1 — preliminary results (~2 weeks)
1. Wire syphilis testing (SyphTest + SyphDx product, basic symptomatic pathway).
2. Port `FetalHealth` from `anc_sti_screening` for APO/ABO accounting (syphilis-driven first).
3. Add DALY post-processing (post-hoc weights on standard outputs).
4. Fix `PartnerNotification` set-and bug locally; add notification-counting results.
5. Add unnecessary-notification metric.
6. Run the three orthogonal sweeps × 20 seeds on uncalibrated default pars in ZW.
7. Generate prelim plots: PN-coverage threshold curves, care-seeking threshold curves, dx×PN interaction.
8. Document methods + outline approach.

**What this prelim does NOT have:** calibration, KE/ZA, full DALY set, PN class promoted to stisim.

### Phase 2 — calibration (handed off to calibration skill)
- ZW first, then KE + ZA.
- Targets: existing ZW data already in `syph_dx_zim`; need KE + ZA equivalents.
- Distinct calibration questions to scope with `calib:getting-started` when ready.

### Phase 3 — promotion + final analysis (~July)
1. Promote `PartnerNotification` (with bug fix and feature parity) to stisim layer 2; submit PR.
2. Fix `gud_syph` and `hiv_bv` connector bugs upstream; submit PRs.
3. Re-run the full scenario grid on calibrated pars across 3 countries.
4. Threshold analyses (minimum PN coverage / care-seeking intensity for X% impact).
5. Decision-relevant analyses: cost per averted APO, EVPI on key parameters (defer to `calib:decision-analysis` skill).

## Next concrete steps (ordered)

1. **Prelim sims working without testing**: confirm uncalibrated 7-disease ZW sim produces sensible directional dynamics over 1990–2040.
2. **Wire syph testing + APO tracking**: port FetalHealth + add SyphDx product.
3. **Fix PN bug + add results**: get the notification-counting metrics in.
4. **Run orthogonal sweeps**: 3 × 4 × 20 seeds = 240 sims.
5. **Plots**: threshold curves + dx×PN interaction.

After step 5: review prelim with stakeholders, decide what to harden for July.
