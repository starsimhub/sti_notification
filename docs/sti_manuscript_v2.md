# False-positive diagnoses and partner notification as point-of-care testing and demand-side interventions for curable STIs scale up in Zimbabwe: a modelling study

*Alternative title: When better STI control erodes test specificity: a modelling study of point-of-care testing, partner notification and demand generation in Zimbabwe*

Robyn M. Stuart, Lori M. Newman, Michael Marks, Griffins Manguro, Chido Dziva Chikwari, Remco P.H. Peters, Darcy W. Rao

*Authors TBC. Target journal: The Lancet Global Health (see `docs/submission_plan.md`).*

> **Status (24 Nov 2026).** This is v2, reframed after co-author review of v1 (`POC STI dx health impact.docx`). Changes from v1:
> - Syphilis has been removed from the model and the paper.
> - POC specificity base case is now 98%, with a 95–99.5% sweep.
> - The partner-notification (PN), care-seeking and condom-counselling ladders are now anchored to Zimbabwean and SSA data.
> - The headline is now the false-positive burden of index cases and notifications, and how it changes as the programme succeeds.
>
> Numbers marked **[XX]** depend on the exp 07 calibration and factorial rerun and must not be quoted until those are complete. Numbers without brackets are from inputs or published literature.

---

# Summary

**Background** Vaginal discharge syndrome (VDS) in sub-Saharan Africa is largely managed syndromically, with substantial overtreatment. Point-of-care (POC) tests for *Neisseria gonorrhoeae* (NG), *Chlamydia trachomatis* (CT) and *Trichomonas vaginalis* (TV) are expected to fix this, and to support more targeted partner notification (PN). But a diagnostic test's positive predictive value depends on prevalence among the people tested. We asked how POC testing combines with demand-side interventions (care-seeking, PN and condom counselling) to reduce curable STIs. We also asked how the share of index cases, and of partner notifications, triggered by false-positive results changes as those interventions succeed.

**Methods** We used STIsim, an agent-based model of co-transmitting HIV, NG, CT, TV and bacterial vaginosis (BV), calibrated to Zimbabwe. We compared syndromic standard of care (SOC) with a POC NG/CT/TV panel (95% sensitivity; 98% specificity in the base case, varied from 95% to 99.5%). On top of POC we layered a full 4 × 4 × 4 factorial of symptomatic care-seeking, PN intensity and condom counselling for the newly treated. Each lever's range was anchored to Zimbabwean and regional data. We projected outcomes over 2027–2040 across [XX] calibrated parameter sets.

**Findings** POC testing alone averted [XX]% (IQR [XX]–[XX]) of new NG, CT and TV infections relative to SOC. It reduced unnecessary NG/CT treatment by [XX]% and cut the share of female index cases who had neither NG nor CT from [XX]% to [XX]%. Combining POC with high-intensity care-seeking, PN and condom counselling averted [XX]% ([XX]–[XX]) of infections. Care-seeking contributed [XX]%, PN [XX]% and counselling [XX]% of this (Shapley decomposition). However, as these levers lowered NG/CT prevalence among women presenting with discharge, from [XX]% to [XX]%, the false-positive share of index cases rose to [XX]% at 98% specificity. Correspondingly, [XX] partner notifications per year were triggered by an index case without NG or CT. Keeping the false-positive share below [XX]% at the high-intensity scenario required a specificity of at least [XX]%.

**Interpretation** POC testing and demand-side interventions together could substantially reduce curable STIs in Zimbabwe. But the false-positive burden of partner notification is not a fixed property of the test. It grows as programmes succeed, because the people presenting with discharge are increasingly likely to have BV rather than NG or CT. Procurement specifications should set specificity with future, not current, prevalence in mind. PN programmes should be designed so that a false-positive notification causes as little harm as possible, for example through provider-assisted notification, safety screening and clear messaging that a partner's test, not the index's, determines the partner's treatment.

**Funding** Gates Foundation.

---

# Research in context

**Evidence before this study** [To complete: PubMed search terms, dates, and summary.] Modelling and empirical studies, including our own, show that POC NG/CT/TV testing substantially reduces overtreatment compared with syndromic management of VDS (Stuart 2026, STI). Empirical work in Zimbabwe and South Africa documents low partner-notification uptake under patient referral: 5.7% of partners of youth were treated in STICH (Lariat 2023), and 27–29% of index cases taking a slip had at least one partner treated in an antenatal setting (Martin 2025). Disclosure carries risks of relationship breakdown and violence. We found no study that quantified how the false-positive share of partner notifications changes as prevalence among the people tested changes under scaled-up STI control.

**Added value of this study** We combine a calibrated transmission model with a full factorial of evidence-anchored demand-side interventions. We show that the false-positive share of index cases and notifications rises as the combined interventions succeed, reaching or exceeding syndromic levels at high intensity unless specificity is very high. We quantify the specificity needed to keep this burden below a given ceiling.

**Implications of all the available evidence** Programmes introducing POC STI tests alongside PN should (i) set specificity requirements against the lower future prevalence their programme aims to achieve, and (ii) build PN pathways that reduce the harm of a false-positive notification.

---

# Introduction

Curable sexually transmitted infections (STIs) remain a major cause of preventable morbidity in sub-Saharan Africa, contributing to pelvic inflammatory disease, infertility, adverse pregnancy outcomes and HIV acquisition (WHO 2021; GBD 2019). Women with vaginal discharge are managed in most of the region by syndromic algorithms. These treat presumptively for NG, CT and TV based on symptoms, risk assessment and, where available, speculum examination (WHO 2021; Zimbabwe MoHCC 2019). Syndromic management guarantees same-day treatment for symptomatic women, but because most VDS is caused by BV, it produces substantial overtreatment (Zemouri 2016; Chirenje 2018). Its effect on undertreatment depends on how it is applied. Among women who present with discharge, sensitivity should approach 100% under a treat-all algorithm, but falls substantially where risk assessment decides who is treated (Cornier 2010). Most asymptomatic infections are, by design, never reached (Fortas 2024).

Overtreatment has costs. Unnecessary antibiotic courses add pressure on supply chains. They may contribute to antimicrobial-resistance selection in NG, although direct evidence that STI overtreatment drives resistance is limited (Wi 2017; Kenyon 2022). For the patient, an STI diagnosis brings a disclosure decision. Disclosure to a partner carries documented risks of blame, accusations of infidelity, relationship breakdown and intimate-partner violence, particularly for women (Mathews 2018; Bennin 2025; Lariat 2023). When the diagnosis is a false positive, those costs are borne for no clinical or epidemiological benefit.

POC etiological tests for NG, CT and TV are expected to reduce overtreatment, and our previous analysis estimated large reductions in unnecessary NG/CT treatment in Zimbabwe (Stuart 2026). They have also been proposed as a platform for more effective demand-side interventions. A definitive same-day diagnosis may encourage symptomatic people to seek care; across sub-Saharan Africa only 66% of women with STI symptoms do so, ranging from 38% to 86% by country (Seidu 2023). It may support more targeted PN, although PN uptake in Zimbabwe has remained low even alongside etiological testing (Lariat 2023; Martin 2025). And it may provide a moment for risk-reduction counselling, which reduced incident STIs by about 30% over 6 months in Project RESPECT (Kamb 1998; Henderson 2020).

What has received less attention is that these levers interact with the test's own performance. The positive predictive value of any test falls as the prevalence of infection among those tested falls. Successful STI control lowers NG/CT prevalence among women presenting with discharge, while BV, which causes most VDS, is unaffected. So the share of positive results, and therefore of index cases and partner notifications, that are false positives should rise as the programme succeeds. If so, the expected reduction in false-positive notifications from replacing syndromic management with POC testing could be partly or wholly eroded over time.

We used a Zimbabwe-calibrated transmission model to address three aims. First, to quantify the reduction in curable STIs achievable by combining POC testing with evidence-anchored levels of care-seeking, PN and condom counselling, and each lever's contribution. Second, to quantify how the false-positive share of index cases and notifications changes across these scenarios. Third, to identify the test specificity needed to keep this false-positive burden below a given ceiling.

# Methods

## Setting

Zimbabwe has a high burden of curable STIs: 23.2% of women aged 16–24 years had CT, NG or TV in the STICH trial (Dziva Chikwari 2023). It also has a generalised HIV epidemic and an established syndromic management programme (Zimbabwe MoHCC 2019). We model the national syndromic algorithm as implemented in Zimbabwe (Figure 1A). Algorithms differ between settings.

## Model

We used STIsim (version 1.5.7), an agent-based model built on Starsim (IDM 2024). It jointly simulates HIV, NG, CT, TV and BV in an age- and risk-structured heterosexual network with marital, casual and transactional partnerships. [XX] agents represent the Zimbabwean population from 1985, scaled to UN population estimates (UN WPP 2022). Natural history, symptomaticity and care-seeking for each pathogen follow our previous analysis (Stuart 2026). BV is modelled as a contributor to VDS but not as an STI. Full model details, an ODD-format description and parameter tables are in the Appendix.

## Calibration

We calibrated eight parameters (HIV, NG, CT and TV transmission probabilities; initial HIV prevalence; three network parameters) by Latin hypercube sampling of 500 parameter sets, each run with five random seeds. Targets were:

- HIV prevalence in adults aged 15–49 years, 2010–20 (ZIMPHIA)
- NG, CT and TV prevalence among women, 2015–25
- Annual NG, CT and TV incidence, 2015–25

[Source for STI targets to confirm.] A parameter set was accepted only if every infection was sustained in at least four of five seeds and every prevalence target lay within half a band-width of its range. We retained the [XX] best-fitting accepted sets. We validated, without fitting, against STICH age-specific prevalence (Dziva Chikwari 2023) and the Zimbabwe STI Etiology Study (Chirenje 2018) (Appendix).

## Standard of care

Under SOC (Figure 1A), women presenting with VDS undergo risk assessment and, where available, speculum examination to assess for cervical infection. Following our previous analysis of how the algorithm is applied in practice (Stuart 2026), 70% of women with and 50% of women without a cervical infection received NG/CT treatment. 65% received metronidazole, and 15%/25% of women with/without cervical infection received no treatment. Men with urethral discharge received NG/CT treatment.

## Point-of-care testing

From 2027 under POC (Figure 1B), people presenting with VDS or urethral discharge, and partners attending through PN, were tested with a multiplex NG/CT/TV panel. The base case was 95% sensitivity and 98% specificity per pathogen, reflecting reported performance of NAAT-based POC assays. [Citation: e.g. Xpert CT/NG / Binx io evaluations.] Specificity was varied from 95% to 99.5%. Only test-positive people were treated, with treatment matched to the pathogen. Presumptive metronidazole for BV was retained at SOC levels.

## Demand-side interventions

We varied three interventions, each at a baseline and three increasing levels (Table 1). All started in 2027 and were layered on POC.

*Symptomatic care-seeking* was scaled by a multiplier on the probability that a person with symptomatic NG, CT, TV or BV seeks care. BV is included because a demand-generation campaign would raise care-seeking for discharge whatever its cause. The female baseline probability (0.49 per symptomatic episode) was multiplied by 1.2, 1.4 and 1.75. The top level corresponds to the highest care-seeking reported in Demographic and Health Surveys across 28 sub-Saharan African countries (86%) and the moderate level to the regional mean (66%) (Seidu 2023).

*Partner notification* varied the probability that an index case notifies each current partner (by stable or casual partnership) and that a notified partner attends (by partnership type and partner sex). The baseline reproduces patient referral as observed in Zimbabwe (Lariat 2023; Martin 2025). The highest level corresponds to provider-assisted referral or expedited partner therapy, under which 69–84% of notified partners sought treatment in small studies in sub-Saharan Africa (Taleghani 2019).

*Condom counselling* enrolled 0%, 25%, 50% or 75% of newly treated people in a 6-month window of 30% lower susceptibility to NG, CT and TV (Kamb 1998; Henderson 2020).

**Table 1.** Intervention levels. Effective reach is the probability that a given male partner of a female index case is notified and attends.

| Intervention | Parameter | Baseline | Low | Moderate | High | Anchor |
|---|---|---:|---:|---:|---:|---|
| Care-seeking | Multiplier on symptomatic care-seeking (female probability) | 1.0 (0.49) | 1.2 (0.59) | 1.4 (0.69) | 1.75 (0.86) | Seidu 2023 |
| PN | Notify, stable / casual | 20% / 10% | 30% / 15% | 45% / 25% | 60% / 35% | Lariat 2023; Martin 2025; Taleghani 2019 |
| PN | Attend, male partner, stable / casual | 50% / 25% | 60% / 35% | 70% / 45% | 85% / 65% | |
| PN | Attend, female partner, stable / casual | 80% / 50% | 85% / 55% | 85% / 60% | 90% / 70% | |
| PN | Effective reach, male partner, stable / casual | 10% / 2.5% | 18% / 5% | 32% / 11% | 51% / 23% | |
| Condom counselling | Coverage of newly treated (30% lower susceptibility, 6 months) | 0% | 25% | 50% | 75% | Kamb 1998; Henderson 2020 |

## Scenarios

We ran SOC plus all 64 POC combinations at 98% specificity. We re-ran six of these at 95%, 99% and 99.5% specificity: POC alone, each lever alone at high, all moderate, and all high. That gives 83 scenarios × [XX] parameter sets × 5 seeds, with seeds paired across scenarios. Outcomes were summed over 2027–2040.

## Outcomes and definitions

- **New infections**: NG + CT + TV.
- **Unnecessary treatment**: a treatment course given to a person not infected with the targeted pathogen at the time of treatment. (v1 called the complementary outcome "successful"; we now use "indicated".)
- **Index case**: a person receiving NG or CT treatment, who then triggers PN. People treated only with metronidazole are excluded from the false-positive measures, because metronidazole treats BV as well as TV.
- **False-positive index case**: an index case who had neither NG nor CT at the time of treatment. Under SOC this arises from presumptive treatment; under POC, from a false-positive test.
- **False-positive share**: false-positive index cases ÷ all index cases, reported separately for women and men.
- **False-positive notification**: a partner notified by a false-positive index case.
- **Presenter prevalence**: NG/CT prevalence among women presenting with discharge, which sets the test's positive predictive value.

Uncertainty is reported as the median and interquartile range across parameter sets. Each lever's contribution to infections averted was estimated by exact Shapley decomposition over the three levers, which gives an answer that does not depend on the order in which they are layered. Code is available at [repository URL].

# Results

*[Results text below is a skeleton: the structure is fixed, the numbers await the rerun. Figure numbers are final.]*

## Calibration and VDS etiology

The [XX] retained parameter sets reproduced HIV, NG, CT and TV targets (Appendix Figure A1). Modelled NG/CT prevalence among women presenting with VDS was [XX]%. BV was present in [XX]% of VDS presentations (Figure 2). [Compare with Chirenje 2018 here or in the Discussion, per D. Rao / R. Peters. Note the model has no candidiasis or idiopathic VDS, so every modelled VDS presentation has at least one of NG/CT/TV/BV.]

## POC testing alone

Relative to SOC, POC alone (98% specificity) averted [XX]% ([XX]–[XX]) of NG/CT/TV infections over 2027–2040 and reduced unnecessary NG/CT treatment by [XX]%. The false-positive share of female index cases fell from [XX]% under SOC to [XX]% (Figure 3).

## Combining POC with demand-side interventions

Infections averted increased with each lever (Figure 4). The high-intensity combination averted [XX]% ([XX]–[XX]). Shapley decomposition attributed [XX]% to care-seeking, [XX]% to PN and [XX]% to condom counselling. Results were similar at moderate intensity (Appendix). Contributions were [near-additive / sub-additive], with an interaction term of [XX]%.

## The false-positive share rises as the programme succeeds

Across all scenarios, the false-positive share of female index cases tracked NG/CT prevalence among women presenting with discharge, closely following the analytic relationship 1 − PPV (Figure 5A). As combined interventions lowered presenter prevalence from [XX]% to [XX]%, the false-positive share rose from [XX]% (POC alone) to [XX]% (all high), [above/below] the SOC level of [XX]% (Figure 5B).

The rise was driven mainly by care-seeking and condom counselling. Both lower NG/CT prevalence among presenters, and care-seeking also brings more BV-only presentations to testing. PN had a smaller effect on the share but the largest effect on the absolute number of false-positive notifications, because it scales all notifications.

## Specificity needed

At 95% specificity the false-positive share of female index cases in the all-high scenario was [XX]%; at 99.5% it was [XX]% (Table 2). Keeping it below [XX]%, the POC-alone level at 98%, required a specificity of at least [XX]%.

**Table 2.** Specificity sweep. Median (IQR).

| Scenario | Specificity | Infections averted (%) | False-positive share, female index cases | False-positive notifications per year | Presenter NG/CT prevalence |
|---|---|---|---|---|---|
| POC alone | 95% / 98% / 99% / 99.5% | [XX] | [XX] | [XX] | [XX] |
| All moderate | … | | | | |
| All high | … | | | | |

## Harm–benefit trade-off

Across the factorial, unnecessary notifications per infection averted ranged from [XX] to [XX] (Figure 6). The ratio was lowest for [XX] and highest for [XX].

# Discussion

Combining POC NG/CT/TV testing with evidence-anchored levels of care-seeking, PN and condom counselling could avert [XX]% of curable STI infections in Zimbabwe over 2027–2040. But the false-positive burden of partner notification is not a fixed property of the test. As the combined interventions lower NG/CT prevalence among women presenting with discharge, an increasing share of positive results, index cases and notifications are false positives. At 98% specificity this share rises from [XX]% with POC alone to [XX]% at high intensity. Much of the reduction in false-positive notifications that POC testing first delivers is lost.

This is a direct consequence of the etiology of VDS. In our model, as in empirical data (Chirenje 2018; Torrone 2018), BV accounts for most presentations, and BV prevalence is unaffected by NG/CT control. So as NG and CT decline, the people presenting with discharge are increasingly women without NG or CT, and the positive predictive value of even a highly specific test falls. This shift in VDS etiology was anticipated by co-authors (R. Peters). It also reflects a broader point (M. Marks): if most VDS is BV, a large share of PN triggered from the VDS pathway will relate to presentations where the NG/CT test adds limited information.

[Para: position relative to Stuart 2026 and to the overtreatment literature. The reduction in unnecessary treatment is robust; the false-positive share of notifications is not.]

[Para: implications for procurement. Specificity requirements should be set against target-state prevalence. Consider confirmatory testing of positives in low-prevalence presenter populations, or a less sensitive but more specific panel for PN triggering. Cost implications.]

[Para: implications for PN design.
- Provider-assisted notification, so the burden is not on the index case.
- Messaging that frames notification as "you may have been exposed; please get tested" rather than "you have an infection".
- Routing partners to testing rather than presumptive treatment, as in our POC arm.
- Safety screening for intimate-partner violence before notification.
- Evidence that PN uptake remains low even with etiological testing (Lariat 2023; Martin 2025), and that STI categories may not carry the same meaning for patients (M. Marks).]

[Para: care-seeking as the largest lever. Barriers include symptom persistence and loss of trust in services, which diagnostics may address (Peters 2019, PMID 31141301). Compare with screening asymptomatic women (L. Newman), which reaches the majority of infections that symptomatic pathways miss, and with integration with HIV prevention, including PrEP (L. Newman).]

**Limitations**

1. Specificity was assumed independent across the three pathogens and constant over time.
2. The model has no candidiasis or idiopathic VDS, which accounted for about a quarter of VDS in Zimbabwe (Chirenje 2018). Including it would lower presenter prevalence further and strengthen our findings.
3. TV can cause cervicitis but is modelled as a vaginal infection only (R. Peters).
4. The model has no HIV–STI cofactor, so we report no HIV outcomes. We do not model the use of STI testing to identify women who may benefit from PrEP (L. Newman).
5. The intervention levels are anchored to observed ranges, but the highest PN level corresponds to provider-assisted referral, which is not routine in Zimbabwe (M. Marks).
6. Effects of condom counselling beyond 6 months were not modelled.
7. Syphilis is excluded. Its partner management (presumptive partner treatment, ANC screening) follows different logic (M. Marks, R. Peters, L. Newman).
8. We report infections averted, not DALYs or costs.
9. Findings are specific to Zimbabwe's prevalence and VDS etiology. The mechanism applies wherever BV dominates VDS.

**Conclusion** POC testing combined with demand-side interventions could substantially reduce curable STIs. Programmes should plan for test specificity and partner-notification safeguards that remain adequate as STI prevalence falls.

---

# Figures (planned)

1. SOC and POC algorithms for VDS. *Edits: add a legend for the blue/salmon boxes (L. Newman #12) and give the speculum examination equal weight with risk assessment (R. Peters #9).*
2. VDS etiology among presenting women, including "no NG/CT/TV" (L. Newman #32). Source: `plotting/plot_slide4_etiology.py` (rebuild).
3. POC alone vs SOC: unnecessary treatment and false-positive share of index cases. Source: `plotting/plot_slide5.py` (rebuild, without syphilis).
4. Infections averted across the factorial, with a Shapley bar inset. Sources: `plotting/plot_slide12.py`, `results/shapley.csv`.
5. False-positive mechanism: (A) false-positive share vs presenter prevalence with analytic curves; (B) false-positive share by intensity and specificity. Source: `analysis/fp_harms.py` → `figures/fig_fp_mechanism.png`.
6. Unnecessary notifications per infection averted. Source: `analysis/fp_harms.py` → `figures/fig_harm_benefit.png`.

Appendix: calibration fit and validation; time series by pathogen (former Figures 4–7, with level values in the captions, L. Newman #48); full factorial heatmaps; ODD model description.

# References (working list, author–year; renumber at formatting)

- Bennin F, et al. Front Reprod Health 2025;7:1640282.
- Chirenje ZM, et al. Sex Transm Dis 2018;45(6):422–428.
- Cornier N, et al. Sex Transm Infect 2010;86(4):303–309.
- Dziva Chikwari C, et al. eClinicalMedicine 2023;62:102125. doi:10.1016/j.eclinm.2023.102125
- Fortas C, et al. PLOS Glob Public Health 2024;4(5):e0003226.
- Henderson JT, et al. JAMA 2020;324(7):682–699. doi:10.1001/jama.2020.10371
- Kamb ML, et al. JAMA 1998;280(13):1161–1167. doi:10.1001/jama.280.13.1161
- Kenyon C, et al. J Antimicrob Chemother 2022;77(9):2411–2427.
- Lariat J, et al. Sex Reprod Health Matters 2023;31(1):2220188. doi:10.1080/26410397.2023.2220188
- Martin K, et al. Lancet Glob Health 2025;13(12):e2097–e2110. doi:10.1016/S2214-109X(25)00306-7
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
- [Add: Michalow J, et al. (PMID 38768094; R. Peters #33); Peters RPH, et al. PN intentions, S Afr Med J (verify); POC NAAT accuracy references for the 98% base case.]
