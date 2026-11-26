# The false-positive share of partner notifications rises as curable STIs decline: a modelling study of point-of-care testing and demand-side interventions in Zimbabwe

*Alternative title: Success erodes specificity: point-of-care STI testing, partner notification and demand generation in Zimbabwe, a modelling study*

Robyn M. Stuart, Lori M. Newman, Michael Marks, Griffins Manguro, Chido Dziva Chikwari, Remco P.H. Peters, Darcy W. Rao

*Authors TBC. Target journal: The Lancet Global Health.*

> **Status (25 Nov 2026).** v3: v2 repitched for The Lancet Global Health. Changes from v2:
> - The headline is the new message: the false-positive share of partner notifications falls when POC testing replaces syndromic management, then climbs back up as STIs decline.
> - The IPSAZ partner-notification trial (Martin 2025) is referenced in the Introduction, Research in context and Discussion.
> - The model is now STIsim on Starsim 4. Non-STI causes of discharge (BV, candidiasis, idiopathic) are modelled together, and recur.
> - The calibration adds HIV mortality, young women's prevalence from STICH and the etiology of VDS presentations (Chirenje 2018) as targets.
>
> Numbers are from `results/headlines.md` (factorial of 25 Nov 2026, `results/scenarios_run_v4c.log`) and `experiments/13_2026-11-25_nonsti_vds/SUMMARY.md`. Check the journal's current word, reference and Summary limits before formatting.

---

# Summary

**Background** Point-of-care (POC) tests for *Neisseria gonorrhoeae* (NG), *Chlamydia trachomatis* (CT) and *Trichomonas vaginalis* (TV) are replacing syndromic management of vaginal discharge syndrome (VDS) in sub-Saharan Africa. They are expected to cut overtreatment and to make partner notification (PN) more targeted. But a test's positive predictive value falls with the prevalence of infection among the people tested. Programmes that pair POC testing with demand generation aim to lower that prevalence. We asked how the share of partner notifications triggered by a false-positive diagnosis changes as those programmes succeed.

**Methods** We used STIsim, an agent-based model of co-transmitting HIV, NG, CT, TV and non-STI causes of vaginal discharge. We calibrated it to Zimbabwe, including the etiology of VDS among women presenting at clinics. We compared syndromic standard of care (SOC) with a POC NG/CT/TV panel (95% sensitivity; 98% specificity, varied from 95% to 99.5%), alone and layered with a 4 × 4 × 4 factorial of care-seeking, PN intensity and condom counselling anchored to Zimbabwean and regional data. We projected 2027–2040 outcomes across 30 calibrated parameter sets.

**Findings** Replacing SOC with POC testing cut the false-positive share of female index cases from 61% (IQR 59–64) to 8% (7–9), and reduced unnecessary NG/CT treatment by 97%. It averted 7·5% (6·8–8·1) of NG, CT and TV infections. Adding high-intensity care-seeking, PN and condom counselling averted 33% (32–35). But as these interventions lowered NG/CT prevalence among women presenting with discharge from 31% to 20%, the false-positive share climbed back to 12% (11–14) at 98% specificity, and to 25% (23–29) at 95%. With more partners notified per index case, false-positive notifications rose six-fold, from about 6800 to 43 000 per year, nearly half the number under SOC. Holding the false-positive share at the POC-alone level required a specificity of about 98·8%.

**Interpretation** The false-positive burden of partner notification is not a fixed property of a test: it rises as STI programmes succeed. Specifications for POC STI tests used to trigger PN should be set against the lower prevalence that programmes aim to reach. PN pathways should be designed so that a false-positive notification does as little harm as possible.

**Funding** Gates Foundation.

---

# Research in context

**Evidence before this study** [To complete: PubMed search terms, dates, and summary.] Modelling and empirical studies show that POC NG/CT/TV testing substantially reduces overtreatment compared with syndromic management of VDS (Stuart 2026). Partner notification remains weak in Zimbabwe even alongside etiological diagnosis.
- In STICH's community-based testing for youth, 5.7% of partners were treated (Lariat 2023).
- In the IPSAZ partner-notification trial, women diagnosed through POC STI screening in antenatal care in Harare had partner treatment within 28 days in 26.6% of cases with a standard PN slip, and 28.7% with a $3 incentive for the partner (odds ratio 1.11, 95% CI 0.66–1.86). No index case had more than one partner treated (Martin 2025).
- Disclosure carries risks of blame, relationship breakdown and intimate-partner violence (Mathews 2018; Bennin 2025).

We found no study that quantified how the false-positive share of partner notifications changes as prevalence among the people tested falls under scaled-up STI control.

**Added value of this study** We combine a transmission model, calibrated to Zimbabwe's HIV epidemic, its curable STI prevalence and the etiology of VDS presentations, with a full factorial of evidence-anchored demand-side interventions. POC testing first cuts the false-positive share of index cases and notifications. That share then climbs back up as the combined interventions reduce NG and CT, because the women presenting with discharge are increasingly those without an STI. We quantify the specificity needed to hold it down.

**Implications of all the available evidence** PN reaches few partners, so each notification carries weight, for good or harm. Programmes introducing POC STI tests alongside PN should:
- set specificity requirements against the lower prevalence their programme aims to achieve;
- build PN pathways that limit the harm of a false-positive notification.

---

# Introduction

Curable sexually transmitted infections (STIs) remain a major cause of preventable morbidity in sub-Saharan Africa. They contribute to pelvic inflammatory disease, infertility, adverse pregnancy outcomes and HIV acquisition (WHO 2021; GBD 2019). Women with vaginal discharge are managed in most of the region by syndromic algorithms. These treat presumptively for NG, CT and TV on the basis of symptoms, risk assessment and, where available, speculum examination (WHO 2021; Zimbabwe MoHCC 2019). Most vaginal discharge, however, is caused by bacterial vaginosis (BV), candidiasis or no identified pathogen. In Zimbabwe's STI Etiology Study, under half of the women presenting with discharge had NG, CT, TV or *Mycoplasma genitalium* (Chirenje 2018). Syndromic management therefore overtreats substantially (Zemouri 2016; Chirenje 2018).

Each presumptive STI diagnosis brings a decision about telling partners. Partner notification (PN) prevents reinfection of the index case and onward transmission. But disclosure carries documented risks of blame, accusations of infidelity, relationship breakdown and intimate-partner violence, particularly for women (Mathews 2018; Bennin 2025; Lariat 2023). When the diagnosis is a false positive, those costs are borne for no clinical or epidemiological benefit.

POC etiological tests for NG, CT and TV are expected to reduce overtreatment, and our previous analysis estimated large reductions in unnecessary NG/CT treatment in Zimbabwe (Stuart 2026). They have also been proposed as a platform for demand-side interventions:
- **Care-seeking:** a definitive same-day diagnosis may encourage people with symptoms to seek care. Across sub-Saharan Africa only 66% of women with STI symptoms do so, ranging from 38% to 86% by country (Seidu 2023).
- **Partner notification:** it may support more targeted PN. Yet PN uptake has stayed low even with etiological diagnosis. In the IPSAZ trial, embedded in a study of POC STI screening among pregnant women in Harare, about a quarter of index cases had a partner treated, and a financial incentive did not change this (Martin 2025). PN therefore reaches few partners, so its yield per notification, and the share of notifications that are false positives, matters.
- **Counselling:** it may provide a moment for risk-reduction counselling, which reduced incident STIs by about 30% over 6 months in Project RESPECT (Kamb 1998; Henderson 2020).

What has received less attention is that these interventions interact with the test's own performance. The positive predictive value of any test falls as the prevalence of infection among those tested falls. Successful STI control lowers NG and CT prevalence among women presenting with discharge, while the non-STI causes of discharge are unaffected. So the share of positive results, and therefore of index cases and partner notifications, that are false positives should climb back up as a programme succeeds. That would erode the reduction in false-positive notifications that replacing syndromic management with POC testing first delivers.

We used a Zimbabwe-calibrated transmission model to address three aims:
1. To quantify how the false-positive share of index cases and notifications changes, from syndromic management to POC testing and across increasingly successful combinations of demand-side interventions.
2. To quantify the reduction in curable STIs that these combinations achieve, and each intervention's contribution.
3. To identify the test specificity needed to keep the false-positive burden below a given ceiling.

# Methods

## Setting

Zimbabwe has a high burden of curable STIs. In the STICH trial's population survey, 25% of women aged 18–24 years in the control arm had CT, NG or TV (Dziva Chikwari 2025). It also has a generalised HIV epidemic and an established syndromic management programme (Zimbabwe MoHCC 2019). We model the national syndromic algorithm as implemented in Zimbabwe (Figure 1A). Algorithms differ between settings.

## Model

We used STIsim (version 2, prerelease), an agent-based model built on Starsim 4 (IDM 2026). It jointly simulates HIV, NG, CT, TV and non-STI causes of vaginal discharge in an age- and risk-structured heterosexual network with marital, casual and transactional partnerships.
- **Population:** 10,000 agents represent the Zimbabwean population from 1985, scaled to UN population estimates. Background mortality excludes AIDS deaths, which the HIV model generates itself, and net emigration follows UN estimates (UN WPP 2022).
- **Condoms:** use follows Zimbabwean survey data and reduces the per-act transmission hazard of each infection by its condom efficacy.
- **Natural history:** symptomaticity and care-seeking for each STI follow our previous analysis (Stuart 2026). The untreated duration of asymptomatic NG was calibrated (below).
- **Non-STI discharge:** BV, candidiasis and idiopathic discharge are modelled together as a non-sexually-transmitted condition. It arises spontaneously in a share of women, is symptomatic in half of episodes and clears, and recurs.

Full model details, an ODD-format description and parameter tables are in the Appendix.

## Calibration

We calibrated ten parameters:
- HIV, NG, CT and TV transmission probabilities;
- initial HIV prevalence and an HIV mortality multiplier;
- the untreated duration of asymptomatic NG;
- three network parameters.

Targets were:
- HIV prevalence in adults aged 15–49 years, 2010–20.
- HIV prevalence, new infections and deaths in the whole population, each averaged over 2000–09 and 2010–21 (UNAIDS). Earlier years were not fitted.
- NG and TV prevalence among adults, 2015–25 (IHME).
- NG, CT and TV prevalence among women aged 18–24 years in the control arm of the STICH population survey, 2021–22 (Dziva Chikwari 2025).
- The share of women presenting with VDS who had none of NG, CT or TV, 2014–16 (about 57%; Chirenje 2018).
- Annual NG incidence, 2015–25 (IHME), within a wider tolerance, since the series is a projection. CT and TV incidence entered the goodness-of-fit score only.

Each disease's targets depend almost entirely on its own parameters. So we first screened 500 parameter sets by Latin hypercube sampling, one seed each, and kept those reaching each disease's targets. We then combined these per-disease sets into 200 candidate parameter sets and ran each with five random seeds.

A parameter set was accepted only if every infection was sustained in at least four of five seeds, and every prevalence target, both HIV mortality targets and the VDS-etiology target lay within half a band-width of its range. 66 of 200 sets were accepted, and we retained the 30 best-fitting. We validated, without fitting, against the share of VDS presentations with NG or CT (about 33%; Chirenje 2018).

## Standard of care

Under SOC (Figure 1A), women presenting with VDS undergo risk assessment and, where available, speculum examination to assess for cervical infection. Following our previous analysis of how the algorithm is applied in practice (Stuart 2026):
- 70% of women with and 50% of women without a cervical infection received NG/CT treatment;
- 65% received metronidazole;
- 15% of women with and 25% without a cervical infection received no treatment.

Men with urethral discharge received NG/CT treatment.

## Point-of-care testing

From 2027 under POC (Figure 1B), people presenting with VDS or urethral discharge were tested with a multiplex NG/CT/TV panel, as were partners attending through PN. The base case was 95% sensitivity and 98% specificity per pathogen, reflecting reported performance of NAAT-based POC assays. [Citation: e.g. Xpert CT/NG / Binx io evaluations.] Specificity was varied from 95% to 99.5%. Only test-positive people were treated, with treatment matched to the pathogen.

## Demand-side interventions

We varied three interventions, each at a baseline and three increasing levels (Table 1). All started in 2027 and were layered on POC.

*Symptomatic care-seeking* was scaled by a multiplier on the probability that a person with symptomatic NG, CT, TV or non-STI discharge seeks care. Non-STI discharge is included because a demand-generation campaign would raise care-seeking for discharge whatever its cause. The female baseline probability for NG and CT (0.49 per symptomatic episode) was multiplied by 1.2, 1.4 and 1.75. The top level corresponds to the highest care-seeking reported in Demographic and Health Surveys across 28 sub-Saharan African countries (86%). The moderate level corresponds to the regional mean (66%) (Seidu 2023).

*Partner notification* varied two probabilities: that an index case notifies each current partner, by stable or casual partnership, and that a notified partner attends, by partnership type and partner sex. The baseline reproduces patient referral as observed in Zimbabwe (Lariat 2023; Martin 2025). The highest level corresponds to provider-assisted referral or expedited partner therapy, under which 69–84% of notified partners sought treatment in small studies in sub-Saharan Africa (Taleghani 2019).

*Condom counselling* enrolled 0%, 25%, 50% or 75% of newly treated people in a 6-month window of 30% lower susceptibility to NG, CT and TV (Kamb 1998; Henderson 2020).

**Table 1.** Intervention levels. Effective reach is the probability that a given male partner of a female index case is notified and attends.

| Intervention | Parameter | Baseline | Low | Moderate | High | Anchor |
|---|---|---:|---:|---:|---:|---|
| Care-seeking | Multiplier on symptomatic care-seeking (female NG/CT probability) | 1.0 (0.49) | 1.2 (0.59) | 1.4 (0.69) | 1.75 (0.86) | Seidu 2023 |
| PN | Notify, stable / casual | 20% / 10% | 30% / 15% | 45% / 25% | 60% / 35% | Lariat 2023; Martin 2025; Taleghani 2019 |
| PN | Attend, male partner, stable / casual | 50% / 25% | 60% / 35% | 70% / 45% | 85% / 65% | |
| PN | Attend, female partner, stable / casual | 80% / 50% | 85% / 55% | 85% / 60% | 90% / 70% | |
| PN | Effective reach, male partner, stable / casual | 10% / 2.5% | 18% / 5% | 32% / 11% | 51% / 23% | |
| Condom counselling | Coverage of newly treated (30% lower susceptibility, 6 months) | 0% | 25% | 50% | 75% | Kamb 1998; Henderson 2020 |

## Scenarios

We ran SOC plus all 64 POC combinations at 98% specificity. We re-ran six of these at 95%, 99% and 99.5% specificity: POC alone, each intervention alone at high, all moderate, and all high. That gives 83 scenarios × 30 parameter sets × 5 seeds, with seeds paired across scenarios. Outcomes were summed over 2027–2040.

## Outcomes and definitions

- **New infections**: NG + CT + TV.
- **Unnecessary treatment**: a treatment course given to a person not infected with the targeted pathogen at the time of treatment.
- **Index case**: a person receiving NG or CT treatment, who then triggers PN. People treated only with metronidazole are excluded from the false-positive measures, because metronidazole treats BV as well as TV.
- **False-positive index case**: an index case who had neither NG nor CT at the time of treatment. Under SOC this arises from presumptive treatment; under POC, from a false-positive test.
- **False-positive share**: false-positive index cases ÷ all index cases, reported separately for women and men.
- **False-positive notification**: a partner notified by a false-positive index case.
- **Presenter prevalence**: NG/CT prevalence among women presenting with discharge, which sets the test's positive predictive value.

Uncertainty is reported as the median and interquartile range across parameter sets. Each intervention's contribution to infections averted was estimated by exact Shapley decomposition over the three, which gives an answer that does not depend on the order in which they are layered. Code is available at [repository URL].

# Results

*[Results text: the structure is fixed; scenario numbers await the factorial run.]*

## Calibration and VDS etiology

The 30 retained parameter sets reproduced the HIV, NG, CT and TV targets (Appendix Figure A1). Among women presenting with discharge in 2014–16:
- 53% (range 50–58%) had none of NG, CT or TV, against about 57% in the Zimbabwe STI Etiology Study (Chirenje 2018).
- 36% (29–41%) had NG or CT, against about 33% (Figure 2).

## POC testing alone

Relative to SOC, POC alone (98% specificity):
- averted 7·5% (IQR 6·8–8·1) of NG/CT/TV infections over 2027–2040;
- reduced unnecessary NG/CT treatment by 97% (97–97);
- cut the false-positive share of female index cases from 61% (59–64) under SOC to 8·1% (7·3–9·0), and of male index cases from 19% (17–22) to 1·1% (0·9–1·3) (Figure 3);
- cut false-positive notifications from about 91 500 to 6800 per year.

## The false-positive share climbs back up as the programme succeeds

Across all scenarios, the false-positive share of female index cases tracked NG/CT prevalence among women presenting with discharge, closely following the analytic relationship 1 − PPV (Figure 5A). As combined interventions lowered presenter prevalence from 31% (POC alone) to 24% (all moderate) and 20% (all high), the false-positive share rose:
- at 98% specificity, from 8·1% to 10·2% (9·3–11·7) and 12·3% (11·1–14·2);
- at 95% specificity, from 17% to 21% and 25%.

These shares stay well below the SOC level of 61% (Figure 5B). The number of false-positive notifications rose further: from about 6800 per year with POC alone to 24 000 (all moderate) and 43 000 (all high), nearly half the 91 500 under SOC.

Care-seeking drove most of the rise in the share. On its own at high intensity it lowered presenter prevalence to 25% and raised the share to 10·6%, because it brings more women with non-STI discharge to testing. PN and condom counselling alone barely changed the share (8·6% and 8·7%). PN had the largest effect on the number of false-positive notifications, because it scales all notifications: on its own at high intensity it raised them five-fold, to about 33 000 per year.

## Infections averted by combining POC with demand-side interventions

Infections averted increased with each intervention (Figure 4). The all-moderate combination averted 23% (21–24) and the all-high combination 33% (32–35). Of the infections averted beyond POC alone at high intensity, Shapley decomposition attributed 14% (13–15) to care-seeking, 58% (56–59) to PN and 28% (27–30) to condom counselling. At moderate intensity the shares were 13%, 53% and 35%.

## Specificity needed

At 95% specificity the false-positive share of female index cases in the all-high scenario was 25% (23–29); at 99·5% it was 4·2% (3·8–4·9) (Table 2). Holding it at the POC-alone level at 98% (8·1%) required a specificity of about 98·8% (interpolated across the sweep).

**Table 2.** Specificity sweep. Median (IQR) across 30 parameter sets; notifications and presenter prevalence are medians.

| Scenario | Specificity | Infections averted (%) | False-positive share, female index cases (%) | False-positive notifications per year | Presenter NG/CT prevalence (%) |
|---|---|---|---|---|---|
| POC alone | 95% | 7·5 (6·8–8·1) | 17·1 (15·7–19·4) | 15 700 | 31·4 |
| | 98% | 7·5 (6·8–8·1) | 8·1 (7·3–9·0) | 6800 | 31·4 |
| | 99% | 7·5 (6·8–8·1) | 4·5 (4·1–5·1) | 3700 | 31·4 |
| | 99·5% | 7·5 (6·8–8·1) | 2·5 (2·4–2·9) | 2100 | 31·4 |
| All moderate | 95% | 22·8 (21·6–24·2) | 21·3 (19·4–24·2) | 55 700 | 24·2 |
| | 98% | 22·7 (21·4–24·1) | 10·2 (9·3–11·7) | 24 300 | 24·3 |
| | 99% | 22·6 (21·4–23·9) | 5·8 (5·3–6·8) | 13 800 | 24·3 |
| | 99·5% | 22·5 (21·3–23·9) | 3·4 (3·1–4·0) | 8400 | 24·3 |
| All high | 95% | 33·6 (32·3–34·8) | 25·1 (22·7–28·7) | 100 000 | 19·6 |
| | 98% | 33·3 (32·1–34·5) | 12·3 (11·1–14·2) | 43 200 | 19·7 |
| | 99% | 33·3 (32·0–34·4) | 7·0 (6·3–8·2) | 24 600 | 19·7 |
| | 99·5% | 33·2 (32·0–34·4) | 4·2 (3·8–4·9) | 15 000 | 19·8 |

## Harm–benefit trade-off

Across the factorial at 98% specificity, false-positive notifications per infection averted ranged from 0·011 to 0·041 (Figure 6). The ratio was lowest for POC with condom counselling alone, and highest for POC with high-intensity care-seeking and PN but no counselling.

# Discussion

Replacing syndromic management with POC NG/CT/TV testing sharply reduces the share of partner notifications triggered by a false-positive diagnosis. But that gain is not permanent. As care-seeking, PN and condom counselling reduce NG and CT, the women presenting with discharge are increasingly those with BV, candidiasis or no identified pathogen. So the positive predictive value of even a highly specific test falls. At 98% specificity the false-positive share of female index cases climbed back from 8% with POC alone to 12% at high intensity, and from 17% to 25% at 95% specificity. Because the same interventions notify more partners per index case, the number of false-positive notifications rose six-fold. Meanwhile the combined interventions averted a third of curable STI infections over 2027–2040.

This is a direct consequence of the etiology of VDS. Under half of the women presenting with discharge in Zimbabwe have an STI (Chirenje 2018), and our calibrated model reproduces this. Non-STI discharge is unaffected by STI control, so its share of presentations can only grow as STIs decline. If most VDS has no STI, much of the PN triggered from the VDS pathway will follow presentations where the test result carries the most risk of being wrong (M. Marks).

The false-positive share matters more because PN reaches so few partners. In the IPSAZ trial, women diagnosed through POC screening in antenatal care in Harare had a partner treated within 28 days in about a quarter of cases, and a financial incentive did not change this (Martin 2025). STICH reported similarly low partner treatment among youth (Lariat 2023). Where few partners are reached, programmes will look to more intensive PN, such as provider-assisted referral, to close the gap. Our results show that such intensification multiplies false-positive notifications along with true ones, and does so at the point where the false-positive share is highest.

[Para: position relative to Stuart 2026 and to the overtreatment literature. The reduction in unnecessary treatment is robust; the false-positive share of notifications is not.]

[Para: implications for procurement. Specificity requirements should be set against target-state prevalence. Consider confirmatory testing of positives in low-prevalence presenter populations, or a more specific panel for PN triggering. Cost implications.]

[Para: implications for PN design.
- Provider-assisted notification, so the burden is not on the index case.
- Messaging that frames notification as "you may have been exposed; please get tested" rather than "you have an infection".
- Routing partners to testing rather than presumptive treatment, as in our POC arm.
- Safety screening for intimate-partner violence before notification.
- Note: IPSAZ shows that incentives to the partner alone do not raise uptake (Martin 2025); STI categories may not carry the same meaning for patients (M. Marks).]

[Para: care-seeking as the largest lever. Barriers include symptom persistence and loss of trust in services, which diagnostics may address (Peters 2019, PMID 31141301). Compare with screening asymptomatic women (L. Newman), which reaches infections that symptomatic pathways miss. Also compare with integration with HIV prevention, including PrEP (L. Newman).]

**Limitations**

1. Specificity was assumed independent across the three pathogens and constant over time.
2. BV, candidiasis and idiopathic discharge are modelled together as one non-STI condition, calibrated to the share of presentations without an STI. The model does not distinguish their treatments, and does not include *M. genitalium*.
3. The modelled CT incidence exceeds IHME estimates while matching prevalence in young women. This suggests shorter CT infections than the IHME estimates imply. TV can cause cervicitis but is modelled as a vaginal infection only (R. Peters).
4. The model has no HIV–STI cofactor, so we report no HIV outcomes. We do not model the use of STI testing to identify women who may benefit from PrEP (L. Newman).
5. The intervention levels are anchored to observed ranges, but the highest PN level corresponds to provider-assisted referral, which is not routine in Zimbabwe (M. Marks).
6. Effects of condom counselling beyond 6 months were not modelled.
7. Syphilis is excluded. Its partner management (presumptive partner treatment, antenatal screening) follows different logic (M. Marks, R. Peters, L. Newman).
8. We report infections averted, not DALYs or costs.
9. Findings are specific to Zimbabwe's prevalence and VDS etiology. The mechanism applies wherever non-STI causes dominate VDS.

**Conclusion** The share of partner notifications triggered by a false positive falls when POC testing replaces syndromic management, then climbs back up as STIs decline. Programmes should plan test specificity and PN safeguards for the prevalence they aim to reach, not the prevalence they start from.

---

# Figures (planned)

1. SOC and POC algorithms for VDS. *Edits: add a legend for the blue/salmon boxes (L. Newman #12) and give the speculum examination equal weight with risk assessment (R. Peters #9).*
2. VDS etiology among presenting women, including "no NG/CT/TV" (L. Newman #32). Source: `plotting/plot_slide4_etiology.py`, reading `results/vds_etiology_presenters.csv`.
3. POC alone vs SOC: unnecessary treatment and false-positive share of index cases. Source: `plotting/plot_slide5.py`.
4. Infections averted across the factorial, with Shapley shares. Sources: `plotting/plot_slide12.py`, `results/shapley.csv`.
5. The false-positive share climbs back up: (A) false-positive share vs presenter prevalence, with analytic curves; (B) false-positive share by intensity and specificity, against the SOC level. Source: `analysis/fp_harms.py` → `figures/fig_fp_mechanism.png`.
6. Unnecessary notifications per infection averted. Source: `analysis/fp_harms.py` → `figures/fig_harm_benefit.png`.

Appendix: calibration fit and validation; time series by pathogen (with level values in the captions, L. Newman #48); full factorial heatmaps; ODD model description.

# References (working list, author–year; renumber at formatting)

- Bennin F, et al. Front Reprod Health 2025;7:1640282.
- Chirenje ZM, et al. The etiology of vaginal discharge syndrome in Zimbabwe: results from the Zimbabwe STI Etiology Study. Sex Transm Dis 2018;45(6):422–428.
- Cornier N, et al. Sex Transm Infect 2010;86(4):303–309.
- Dziva Chikwari C, et al. Evaluation of a community-based aetiological approach for sexually transmitted infections management for youth in Zimbabwe: intervention findings from the STICH cluster randomised trial. eClinicalMedicine 2023;62:102125. doi:10.1016/j.eclinm.2023.102125
- Dziva Chikwari C, et al. Effect of a community-based intervention for sexually transmitted infections on population-level prevalence among youth in Zimbabwe (STICH): a cluster-randomised trial. Lancet Glob Health 2025;13(1):e134–e145. doi:10.1016/S2214-109X(24)00373-5
- Fortas C, et al. PLOS Glob Public Health 2024;4(5):e0003226.
- Henderson JT, et al. JAMA 2020;324(7):682–699. doi:10.1001/jama.2020.10371
- Kamb ML, et al. JAMA 1998;280(13):1161–1167. doi:10.1001/jama.280.13.1161
- Kenyon C, et al. J Antimicrob Chemother 2022;77(9):2411–2427.
- Lariat J, et al. Sex Reprod Health Matters 2023;31(1):2220188. doi:10.1080/26410397.2023.2220188
- Martin K, Dziva Chikwari C, Dauya E, et al. Financial incentives to improve uptake of partner treatment for sexually transmitted infections in Zimbabwe antenatal care: a cluster randomised trial (IPSAZ). Lancet Glob Health 2025;13(12):e2097–e2110. doi:10.1016/S2214-109X(25)00306-7. [Verify title and pages against the published version; the results quoted here are from the authors' conference abstract and the trial registration, PACTR202302702036850.]
- Mathews C, et al. Sex Transm Infect 2018;94(2):144–150.
- Peters RPH, et al. [community hidden-burden study], PMID 31141301. [Verify citation.]
- Seidu A-A, et al. Sex Transm Infect 2023;99(5):296–302. doi:10.1136/sextrans-2022-055424
- Stuart RM, et al. Sex Transm Infect 2026; sextrans-2025-056646.
- Taleghani S, et al. Int J STD AIDS 2019;30(3):292–303. doi:10.1177/0956462418803983
- Torrone EA, et al. PLOS Med 2018;15(2):e1002511.
- Wi T, et al. PLOS Med 2017;14(7):e1002344.
- WHO. Guidelines for the management of symptomatic STIs. 2021.
- Zemouri C, et al. PLoS One 2016;11(10):e0163365.
- Zimbabwe MoHCC. National STI management guidelines 2019–2021.
- [Add: Michalow J, et al. (PMID 38768094; R. Peters #33); Peters RPH, et al. PN intentions, S Afr Med J (verify); POC NAAT accuracy references for the 98% base case; UNAIDS and IHME data sources.]
