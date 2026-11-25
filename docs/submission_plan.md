# Submission plan: STI notification manuscript (v2)

*Prepared 24 Nov 2026. Branch: `reframe/no-syph-fp-harms`.*

## 1. Target journals

| Rank | Journal | Why | Watch-outs |
|---|---|---|---|
| 1 | **The Lancet Global Health** | Published the IPSAZ PN-incentive trial (Martin 2025), so the editors know the PN problem in Zimbabwe. LMIC-focused; takes policy-relevant modelling. The "success erodes specificity" message is new and actionable for procurement. | Short format (check current word, reference and abstract limits on the journal site; I could not confirm them). Requires a *Research in context* panel (drafted in v2). Will expect tight calibration and clear uncertainty, so exp 07 must fix the spread across parameter sets. |
| 2 | **PLOS Medicine** | No length limit; prefers a ≤300-word abstract. Requires an EQUATOR reporting checklist and an Author Summary at revision. Good home for a mechanism-plus-policy modelling paper. | Lower turnaround certainty. |
| 3 | **eClinicalMedicine** / **BMJ Global Health** | STICH primary paper is in eClinicalMedicine. Both are open access and take modelling. | — |
| Fallback | **Sex Transm Infect** / **Sex Transm Dis** | The companion VDS paper is in STI. | Lower reach. |

Reporting: use the ODD protocol for the agent-based model description (Appendix), and state adherence to modelling good-practice guidance (e.g. ISPOR-SMDM). Data and code availability: the public GitHub repo plus a Zenodo DOI for the results files.

## 2. What must happen before submission (in order)

1. **Smoke-test the code changes on the VM.** I could not run the model in my sandbox.
   ```bash
   conda run -n starsim python model.py
   conda run -n starsim env N_DRAWS=4 K_SEEDS=2 N_AGENTS=5000 STOP=2026 N_WORKERS=8 \
       python experiments/07_2026-11-24_no_syph_calibration/run.py
   ```
2. **Run the exp 07 calibration** (500 draws × K=5, 20k agents, STOP=2030):
   ```bash
   conda run -n starsim env N_DRAWS=500 N_WORKERS=120 \
       python experiments/07_2026-11-24_no_syph_calibration/run.py
   ```
   Check that at least 30 draws are accepted and that the spread across retained draws is tight. If fewer pass, relax `ACCEPT_TOL` or widen priors. Write `SUMMARY.md`.
3. **Run the scenarios** (83 cells × N draws × 5 seeds):
   ```bash
   conda run -n starsim env SMOKE=1 N_WORKERS=30 python run_scenarios.py
   conda run -n starsim env N_DRAWS=30 N_SEEDS=5 N_WORKERS=120 python run_scenarios.py
   conda run -n starsim python process_results.py
   conda run -n starsim python analysis/fp_harms.py
   ```
   At 20k agents and 83 cells, expect about 2–3× the previous 4 h per 10 draws. Consider N_DRAWS=20 if compute is tight.
4. **Fill in the [XX] values** in `docs/sti_manuscript_v2.md` from `results/fp_cells.csv`, `fp_spec_sweep.csv` and `shapley.csv`.
5. **Rebuild Figures 2–4 without syphilis.** Figures 5–6 come from `analysis/fp_harms.py`. Fix Figure 1 per L. Newman #12 and R. Peters #9.
6. **References**: resolve placeholders, add POC NAAT accuracy citations for the 98% base case, and renumber.
7. **Circulate v2 to co-authors** with the response table below; then do the journal formatting.

## 3. Open decisions for Robyn

- **STI calibration targets.** `data/zimbabwe_sti_data.csv` looks like projections (it runs to 2040). Confirm its source and denominators: ng/tv `prevalence_f` vs overall; ct uses `prevalence_f_25_30`. Exp 07 fits 2015–25 rather than exp 06's 2035–40.
- **BV care-seeking.** I added BV to the care-seeking lever, on the grounds that campaigns raise care-seeking for discharge whatever its cause. This makes the false-positive effect stronger. Keep it, or run both?
- **Confirmatory testing arm.** It is not implemented. Worth adding if reviewers ask, or as a discussion point only?
- **Agent count.** Raised to 20k (from 10k) to reduce NG fade-out. This is the main compute cost driver.

## 4. Response to co-author comments on v1

| # | Who | Comment (short) | Action in v2 |
|---|---|---|---|
| 0 | CDC | "Undertreatment" in title; syndromic management also overtreats | New title; framing is now false positives / PN |
| 1 | RP | Limited evidence that overtreatment drives AMR | Caveated in the Introduction |
| 2 | RP | Don't abbreviate SM | Done |
| 3 | RP | Treat-all vs risk-assessment sentence deserves emphasis | Kept, more prominent |
| 4 | LN | What does 62.5% (Cornier) mean? | TODO: clarify in text (risk-assessment algorithm, symptomatic women) |
| 5, 56 | LN | STI testing as a gateway to PrEP; HIV limitation | Discussion and limitation 4 |
| 6 | MM | PN still low with etiological testing; etiology may not carry meaning | Introduction and Discussion |
| 7, 10, 15, 19, 41, 44–45, 58 | RP, LN | Remove syphilis | **Removed from model and paper** |
| 8 | RP | State that the SOC is Zimbabwe-specific | Methods |
| 9, 13 | RP | Give exam equal weight with risk assessment | Methods; Figure 1 TODO |
| 11 | LN | Not all ANC RDT positives treated | Moot (syphilis removed) |
| 12 | LN | Figure 1 box colours need a legend | Figure 1 TODO |
| 14 | MM | No treatment for negatives? | Methods: only test-positives treated; BV metronidazole retained |
| 16 | MM | Treat syphilis partners presumptively | Moot (syphilis removed) |
| 17 | RP | Partner number and concurrency assumptions | TODO: Appendix table from `results/pn_partner_counts.csv` |
| 18, 27, 57 | MM | Where are PN rates from? High rungs a stretch | **Ladder re-anchored** (Table 1; Lariat 2023, Martin 2025, Taleghani 2019) |
| 20 | DR | Care-seeking multipliers anchored? | **Anchored** to Seidu 2023 (66% mean, 86% max) |
| 21–22 | DR, RP | Partners likely treated presumptively for NG/CT | Discussion; possible sensitivity analysis |
| 23 | MM | 50% condom effect optimistic | **Now 30%** (Kamb 1998; Henderson 2020) |
| 24 | LN | Define "bundled prevention" | Renamed "condom counselling" and defined |
| 25–26 | DR | Sex-specific notification probabilities | Possible extension; the model already varies attendance by sex. TODO: ask Maricianah's group |
| 28–29 | DR, MM | "Successful" → "indicated" | Done |
| 30–31, 34–36 | DR, MM, RP | Move etiology comparison; what does BV-dominant VDS mean for PN? | Comparison moved to Results/Discussion; MM's point is now a central argument |
| 32 | LN | Candida; women with none of these infections | Figure 2 adds "none"; limitation 2 |
| 33 | RP | Cite Michalow | Reference added (verify) |
| 37–38 | RP, MM | VDS etiology shifts as STIs decline | **This is now the core mechanism** (Figure 5) |
| 39 | RP | TV can cause cervicitis | Limitation 3 |
| 40 | MM | NAATs are 98–99% specific | **Base case 98%, sweep 95–99.5%** |
| 42 | LN | Clarify population | Tables now say "women presenting with VDS" |
| 43, 46 | MM | Give numbers; POC vs PN — which drives more? | Shapley decomposition |
| 47 | LN | What's happening with syphilis incidence? | Moot. The cause was treated agents returning to fully susceptible (reinfection churn) |
| 48 | LN | Put level values in captions | Appendix captions |
| 49 | LN | TV claim doesn't match the figure | Text to be rewritten from the new results |
| 50 | LN | Does layering order matter? | Shapley decomposition answers this directly |
| 51–52 | LN, RP | Repeat IPV references in Discussion | Done |
| 53 | RP | Define "false alarm" | Defined: "false-positive index case" (Methods) |
| 54–55 | LN, RP | Symptomatic care vs screening | Discussion paragraph; cite Peters 2019 |
