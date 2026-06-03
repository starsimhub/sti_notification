# Syphilis diagnostic algorithm for antenatal care — Zimbabwe

Summary of the maternal syphilis diagnostic/screening algorithm, its historical
evolution, and **implementation guidance for modelling the time-varying testing
algorithm in this repo**.

Sources: *WHO guideline on syphilis screening and treatment for pregnant women*
(WHO, 2017; `docs/who-syphilis-anc.pdf`) for the current end-state, plus the
literature cited in §3 for the historical trajectory.

> **For the implementing agent:** the actionable content is §6 (tests + timelines)
> and §7 (the code change). §1–§5 are the clinical/historical rationale. The single
> most important correction: **the ANC screen is serology, not the GUD/ulcer test.**
> The model currently uses the `gud` product for the ANC test — this is wrong (it
> only catches primary syphilis). See §7.

---

## 1. Two distinct detection channels — do not conflate them

Maternal syphilis was *never* controlled through a single algorithm. Throughout the
whole period there have been **two parallel channels**, and they detect different
things:

| Channel | Who it reaches | Test | Stages detected |
|---|---|---|---|
| **ANC serological screening** | Asymptomatic pregnant women at ANC | **RPR/VDRL → (TPHA) confirm**, later treponemal RST | Primary → latent → tertiary (the backbone) |
| **Syndromic GUD management** | *Symptomatic* people with a genital ulcer, at any clinic | None — treat the syndrome | Primary (ulcer-stage) only |

Syndromic GUD management treats ulcers presumptively (in Zimbabwe: benzathine
penicillin + erythromycin + acyclovir, covering syphilis, chancroid, LGV, HSV). It
catches only the small ulcer-stage window and only among care-seekers — it is **not**
and never was the antenatal screen. Serology has always been the ANC backbone because
it detects the latent/secondary infection that dominates the prevalent pool.

**The historical failure was coverage, not test choice.** In Murewa District in the
late 1990s only **20% of first-visit ANC attendees were screened** despite a 9.2%
seroprevalence — the RPR test existed and worked; women weren't reaching it or weren't
getting results/treatment before delivery. Coverage (and result-return), not test
sensitivity, is the lever that changed over time.

---

## 2. Current algorithm (WHO 2017) — which strategy applies to Zimbabwe

WHO classifies settings at a **5% antenatal prevalence threshold**. Repo data
(`data/zimbabwe_syph_data.csv`) puts active prevalence at ~1.7–2.2% → Zimbabwe is
**low-prevalence**, so WHO suggests **Strategy A: a single on-site rapid syphilis test
(RST), treat if positive**, at the first ANC visit (Recommendations 1 + 3).

```
   First ANC visit ──► On-site treponemal RST ──► positive ──► TREAT (same visit)
   [Zimbabwe: dual HIV/syphilis RDT]           └► negative ──► no treatment
```

Treponemal caveat: the RST stays positive for life and cannot distinguish active from
past, treated infection. Where resources allow (Strategy C), a quantitative RPR after a
positive RST confirms activity and stages early vs late.

---

## 3. Historical evolution of the ANC algorithm

The **test technology** changed; the **channel logic** (serology screen + separate
syndromic channel) did not.

### 1980s — off-site non-treponemal serology
- **RPR (± VDRL)** drawn at ANC, sent to a district/central lab. **TPHA/FTA-ABS
  confirmation only at reference labs** (Harare).
- Dominant failure: **off-site → loss to follow-up.** Results returned after delivery
  or never; treatment frequently missed.
- Treatment (benzathine penicillin) unchanged from then to now.

### 1990s — syndromic management formalised; serology still the ANC screen
- WHO **syndromic management** flowcharts (1991/1994); **Zimbabwe an early adopter.**
  GUD flowchart treated syphilis **and** chancroid — chancroid was a major GUD cause in
  southern Africa then (has since collapsed; HSV-2 now dominates GUD).
- ANC screen **remained RPR serology**; push toward **on-site RPR** to cut LTFU, driven
  by the HIV epidemic (ANC HIV prevalence climbing toward ~25–30%).
- Coverage still low (~20%, Murewa).

### 2000s — on-site RPR; POC treponemal emerging; system shock
- **RPR remained the ANC mainstay.** WHO 2003 STI guidelines in force.
- **Rapid treponemal POC tests (RSTs)** emerged / were field-evaluated mid-to-late
  decade; limited rollout.
- **PMTCT/EMTCT integration** began bundling syphilis with HIV testing.
- **Zimbabwe-specific shock:** the **~2007–2009 economic collapse** gutted reagent/
  kit supply and lab services — coverage *degraded* mid-decade, not a smooth rise.

### 2010s → present — dual HIV/syphilis treponemal RDT
- **Dual HIV/syphilis RDT** (treponemal-first, same-visit) scaled within EMTCT;
  regional comparators adopted ~2011 (Zambia national policy), Zimbabwe firmly in the
  2010s. Supplements rather than replaces the underlying serology logic.

---

## 4. Treatment by stage (WHO Rec. 5–8) — unchanged across eras

First-line **benzathine penicillin G**. *Avoid ANC stock-outs.*

| Stage | Regimen |
|---|---|
| Early (≤2 yrs) | 2.4 MU IM, single dose |
| Late / unknown (>2 yrs) | 2.4 MU IM weekly × 3 (interval ≤14 days) |

Penicillin alternatives only if unavoidable; **no doxycycline in pregnancy**;
erythromycin/azithromycin don't fully cross the placenta → **treat the newborn**.

---

## 5. Test interpretation (WHO §5.4)

- **Non-treponemal (RPR/VDRL):** positive ~4–6 wks post-infection; **titres fall with
  treatment** → can revert to negative → marks *active* infection. False-neg in very
  early primary and late latent.
- **Treponemal (TPHA/TPPA/RST):** positive earlier; **stays positive for life (~85%)**
  → marks *exposure*, not activity.

---

## 6. IMPLEMENTATION — tests + timelines for the model

The `data/syph_dx.csv` products encode different test behaviours. Map them to eras as
follows. **Two channels run in parallel the whole time**; only the ANC serology product
and the coverage ramp change.

### 6a. ANC serological screen (the backbone — currently mis-wired, see §7)

| Era | Real-world test | `syph_dx.csv` product | Why |
|---|---|---|---|
| ~1980–2010 | RPR / VDRL (non-treponemal) | **`confirm`** | High sens primary→tertiary (0.9), low in naive/treated (0.05) — matches non-treponemal: detects active infection, titres fall after treatment |
| ~2010–present | Dual HIV/syphilis treponemal RDT | **`dual`** | Stays positive in past-infected (`sus_not_naive` 0.95) — matches treponemal lifelong positivity; primary 0.2 reflects slow early turn-positive |

> Do **not** use `gud`/`gud2` for the ANC screen — those are ulcer/clinical products
> (high only in primary). They belong to the symptomatic channel.

### 6b. Symptomatic / syndromic GUD channel (runs throughout, unchanged)

| Channel | Product | Note |
|---|---|---|
| Symptomatic ulcer/rash presentation | **`gud`** (or `syndromic_gud`) | Already wired via `syph_symp_test`; catches ulcer-stage care-seekers. Keep. |

### 6c. Proposed ANC coverage timeline (`anc_test_prob`)

These are **proposed starting values to calibrate**, not measured facts. Ground truth
anchor: ~20% screened in late-1990s Murewa. Shape: low and off-site early, rising with
on-site RPR, **dip ~2008** (economic collapse), steep EMTCT-era climb.

| Year | Proposed `anc_test_prob` | Rationale |
|---|---|---|
| 1980 | ~0.05 | Off-site RPR, severe LTFU |
| 1990 | ~0.15 | On-site RPR push begins |
| 1999 | ~0.20 | Murewa anchor |
| 2008 | ~0.20 (dip from trend) | Economic/health-system collapse |
| 2012 | ~0.50 | EMTCT scale-up |
| 2018+ | ~0.85–0.95 | Dual RDT, EMTCT validation targets (≥95%) |

Implement as a time-varying series (interpolated), not a step. The **product switch**
(`confirm` → `dual`) is a separate ~2012–2015 transition, gated by start/stop year.

### 6d. Treatment

Single `SyphTx` keyed to stage (early single dose vs late ×3) — already represented by
`SyphTx`. No era dependence needed.

---

## 7. The specific code change

`make_syph_testing()` in [interventions.py](../interventions.py) currently builds the
ANC test from the **`gud`** product:

```python
gud_dx = sti.SyphDx(syph_dx_df[syph_dx_df.name == 'gud'], ...)   # ulcer test
...
syph_anc_test = sti.SyphTest(name='syph_anc_test', product=gud_dx, ...)  # ← WRONG
```

This gives the antenatal screen ~5% sensitivity for latent/secondary syphilis — it can
essentially only find primary infection, contradicting how ANC serology has always
worked. Required changes:

1. **Build a serology product for the ANC test** — `confirm` (RPR era) and `dual`
   (RDT era), not `gud`.
2. **Make the ANC product era-dependent**: register two ANC `SyphTest` instances gated
   by year — `confirm` until ~2012, `dual` after — using the existing start/stop
   pattern (cf. `synd_end`/`intv_year` in `make_testing`).
3. **Make `anc_test_prob` time-varying** per §6c (interpolated series with the 2008
   dip), replacing the scalar default.
4. **Leave the symptomatic channel on `gud`** — it correctly represents ulcer-stage
   syndromic detection.

Keep the two channels separate; both feed the single `SyphTx` via the existing
`syph_dx_eligibility` union.

---

## 8. Open questions / flags for the implementer

Judgment calls and uncertainties baked into §6–§7 — resolve these before/while implementing.

1. **`confirm` vs a dedicated `rpr` row.** §6a reuses the `confirm` product for the RPR
   era because its profile (high primary→tertiary, low in naive/treated) matches
   non-treponemal behaviour. But `confirm` is named/used as a *confirmatory* test
   elsewhere — consider adding a purpose-built `rpr` row to `data/syph_dx.csv` instead of
   overloading `confirm`.
2. **`dual` primary sensitivity = 0.2 looks wrong.** Real treponemal tests turn positive
   *early* (often before non-treponemal). The model encodes primary 0.2, which understates
   early detection by the RDT. Verify against the source of these values and adjust if it's
   an artefact.
3. **Coverage values (§6c) are uncalibrated proposals.** Only the ~20% late-1990s Murewa
   point is data-anchored. The 1980/1990/2012/2018 values and the curve shape are guesses to
   be calibrated, not facts.
4. **The 2008 dip is qualitative.** The economic-collapse disruption is well-documented in
   direction but not quantified here — magnitude/duration need a source or calibration.
5. **Dual-RDT adoption year for Zimbabwe is unconfirmed.** §6 uses ~2012–2015 as the
   `confirm`→`dual` switch from regional comparators; pin the actual national rollout year
   if a source is available.
6. **Treponemal lifelong positivity → over-treatment.** Switching the ANC screen to `dual`
   (treponemal, `sus_not_naive` 0.95) means previously-treated women re-screen positive and
   may be re-treated each pregnancy. This is real-world behaviour (WHO §5.3, Strategy A) but
   confirm the model handles it as intended rather than as spurious incidence.
7. **API assumptions to verify.** §7 assumes `sti.SyphTest` supports (a) a time-varying
   `test_prob_data` series and (b) `start`/`stop` year gating for the era switch. Confirm
   against the `stisim` API before relying on them.

---

*WHO guideline on syphilis screening and treatment for pregnant women. Geneva: WHO;
2017. CC BY-NC-SA 3.0 IGO. Treatment adapted from WHO treatment guidelines for*
Treponema pallidum *(syphilis), 2016.*

**Historical sources:**
- Syphilis in Murewa District, Zimbabwe — coverage/seroprevalence. https://pubmed.ncbi.nlm.nih.gov/10101428/
- Seroprevalence of syphilis, Harare Maternity Hospital. https://pubmed.ncbi.nlm.nih.gov/17892228/
- Zimbabwe STI Etiology Study (GUD aetiology; chancroid collapse). https://pubmed.ncbi.nlm.nih.gov/29240636/
- POC STI screening integration in Zimbabwe ANC. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12684121/
- POC syphilis in Zambia ANC, national rollout (regional comparator). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4430530/
