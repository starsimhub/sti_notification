# Closing the undertreatment gap: the health impact of demand-generation and diagnostic strategies for sexually transmitted infections in Zimbabwe

*Working title. Authors, affiliations, abstract, methods, results, and discussion TBD — see [`ANALYSIS_PLAN.md`](../ANALYSIS_PLAN.md) for scope, endpoints, and current calibration status.*

# Introduction

Curable sexually transmitted infections (STIs) — gonorrhoea (NG), chlamydia (CT), trichomoniasis (TV), and syphilis — remain a major cause of preventable morbidity in sub-Saharan Africa, contributing to pelvic inflammatory disease, infertility, adverse pregnancy and birth outcomes, and onward HIV transmission \[1,2\]. Zimbabwe illustrates the scale of the problem: STICH, a cluster-randomised trial among youth, found that nearly a quarter of young women aged 16–24 had at least one of NG, CT, or TV in 2020 \[3\], syphilis seroprevalence among adults is estimated at around 1–3% \[4\], and the country's generalized HIV epidemic (adult prevalence ~11%) compounds the consequences of untreated STIs. The World Health Organisation recommends syndromic management — treating a presenting symptom rather than a laboratory-confirmed infection — as the standard of care in settings without diagnostic capacity \[1\].

Whether a curable infection is ultimately cured depends on two largely independent factors: the accuracy of the diagnostic pathway, and whether the infected person — and their partners — reach that pathway at all. Two companion analyses to this one focus on the first factor. Stuart et al. model the impact of a point-of-care (POC) diagnostic for NG/CT/TV on overtreatment and undertreatment relative to different implementations of syndromic management for vaginal discharge syndrome (VDS) in Zimbabwe \[5\], and a parallel analysis quantifies the overtreatment avoidable with improved active-syphilis diagnostics against the current antenatal and syndromic screening algorithms \[6\]. Both studies hold care-seeking and partner management fixed and vary only diagnostic accuracy — the supply side of the treatment cascade.

Figure 1, reproduced from the companion VDS diagnostics analysis \[5\], illustrates this supply-side lever concretely. Panel A shows the syndromic-management pathway: a woman presenting with VDS undergoes a risk assessment and physical exam, which — depending on whether she has a true cervical infection — routes her along a branching set of treatment outcomes for NG/CT, BV/TV, both, or neither; because the exam and risk assessment are imperfect proxies for infection status, a substantial share of women with an infection are missed while a substantial share without one are treated anyway. Panel B shows the corresponding POC pathway: a multiplex test for NG/CT/TV separates treatment of identified infections from the (unchanged) presumptive treatment of possible bacterial vaginosis, sharply reducing the overtreatment and undertreatment introduced by the risk-assessment step in panel A. The same syndromic-management-vs-POC contrast is used as the diagnostic-accuracy arm of the model presented here (the `poc=` flag in `make_testing`; see [`ANALYSIS_PLAN.md`](../ANALYSIS_PLAN.md)), making Figure 1 a shared reference point across all three analyses.

![Figure 1](../figures/fig1_algos.png)

*Figure 1. Standard-of-care syndromic management (panel A) and a hypothetical augmented algorithm with a point-of-care diagnostic for NG/CT/TV (panel B), for women presenting with vaginal discharge syndrome. Adapted from the companion analysis of diagnostic accuracy for VDS management in Zimbabwe \[5\].*

Diagnostic accuracy, however, only determines treatment outcomes for people who present for care in the first place. Across sub-Saharan Africa, an estimated 66% of women with STI symptoms seek healthcare, ranging from 38% to 86% across countries \[7\] — meaning that even a perfectly accurate test at the point of care cannot close the undertreatment gap for the third or more of symptomatic women who never present. Partner notification (PN) — informing an index patient's sexual partners of their exposure so they, too, can be tested and treated — is the complementary lever for reaching people who would not otherwise present symptomatically, and is essential for preventing reinfection of the index case. Yet a Cochrane review of PN strategies found no single approach reliably superior across settings, with especially limited evidence from HIV/syphilis and from resource-limited countries \[8\]. Provider-delivered alternatives such as expedited or accelerated partner therapy — supplying treatment for partners without requiring their own clinical visit — have shown high acceptability where piloted, including among adolescent girls and young women in Kenya \[9,10\], but are not yet part of standard practice in the region. PN is also not without risk: an observational study in Cape Town found that intimate-partner violence following STI disclosure was a real and non-trivial concern, particularly in casual or already-strained relationships \[11\] — a harm that is compounded when notification is triggered by a false-positive diagnosis rather than a true infection.

This study is the demand-side companion to \[5,6\]: rather than varying diagnostic accuracy alone, we hold a Zimbabwe-calibrated STIsim model \[12\] of co-transmitting HIV, syphilis, NG, CT, TV, and BV fixed on its calibrated transmission parameters, and layer in symptomatic care-seeking, partner-notification intensity, and bundled prevention (condoms and counselling for the diagnosed) as independent, combinable levers alongside the SOC/POC diagnostic contrast from Figure 1. Our aim is to quantify how far demand-generation strategies alone can close the undertreatment gap, identify the threshold levels of care-seeking and PN reach needed for meaningful reductions in adverse pregnancy/birth outcomes and disability-adjusted life years, and assess whether improved diagnostic accuracy reduces the burden of *unnecessary* partner notification — and its associated harms — alongside unnecessary treatment.

# Methods

*TODO.*

# Results

*TODO — pending headline scenario run (see [`ANALYSIS_PLAN.md`](../ANALYSIS_PLAN.md), "Next concrete steps").*

# Discussion

*TODO.*

# References

1\. World Health Organisation. Guidelines for the management of symptomatic sexually transmitted infections. Geneva: WHO; 2021.

2\. Vos T, Lim SS, Abbafati C, et al. Global burden of 369 diseases and injuries in 204 countries and territories, 1990–2019: a systematic analysis for the Global Burden of Disease Study 2019. Lancet. 2020;396(10258):1204–1222.

3\. Chikwari CD, Simms V, Kranzer K, Dauya E, Bandason T, Tembo M, et al. Evaluation of a community-based aetiological approach for sexually transmitted infections management for youth in Zimbabwe: intervention findings from the STICH cluster randomised trial. eClinicalMedicine. 2023;62:102125.

4\. Ruangtragool L, Silver R, Machiha A, et al. Factors associated with active syphilis among adults 15 years and older: Zimbabwe Population-based HIV Impact Assessment, 2015–2016. PLOS ONE. 2022.

5\. Stuart RM, Newman L, Manguro G, Dziva Chikwari C, Marks M, Peters RPH, et al. Reduction in overtreatment of gonorrhea and chlamydia through point-of-care testing compared with syndromic management for vaginal discharge: a modeling study for Zimbabwe. [Companion manuscript, `stisim_vddx_zim`, in preparation.]

6\. Stuart RM, et al. Estimating the value of novel tests for active syphilis in Zimbabwe: how much overtreatment can be avoided? [Companion manuscript, `syph_dx_zim`, in preparation.]

7\. Seidu A-A, Aboagye RG, Okyere J, Adu C, Aboagye-Mensah R, Ahinkorah BO. Towards the prevention of sexually transmitted infections (STIs): healthcare-seeking behaviour of women with STIs or STI symptoms in sub-Saharan Africa. Sex Transm Infect. 2023;99(5):296–302.

8\. Ferreira A, Young T, Mathews C, Zunza M, Low N. Strategies for partner notification for sexually transmitted infections, including HIV. Cochrane Database Syst Rev. 2013;(10):CD002843.

9\. Golden MR. Expedited partner therapy for sexually transmitted diseases. Clin Infect Dis. 2005;41(5):630–633.

10\. Omollo V, et al. A pilot evaluation of expedited partner treatment and partner HIV self-testing among adolescent girls and young women diagnosed with *Chlamydia trachomatis* and *Neisseria gonorrhoeae* in Kisumu, Kenya. Sex Transm Dis. 2021;48(10):766–772.

11\. Mathews C, Kalichman MO, Laubscher R, Hutchison C, Nkoko K, Lurie M, Kalichman SC. Sexual relationships, intimate partner violence and STI partner notification in Cape Town, South Africa: an observational study. Sex Transm Infect. 2018;94(2):144–150.

12\. Institute for Disease Modeling. Starsim. 2024.
