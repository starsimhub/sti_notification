# Exp 06 — condoms/counselling-for-the-diagnosed ladder

**Question.** Exp 04 found CT reinfection is driven by the *cured index*
being reinfected by still-untreated concurrent partners, with a residual
floor PN reach alone can't clear. So: **does protecting the diagnosed
agent for a window after treatment (condoms/counselling → reduced
re-acquisition) reduce CT reinfection/prevalence — and how does its
dose-response compare to scaling PN (exp 05)?**

**Plan.** POC arm + *baseline* PN (×1, the common base with exp 05 rung
x1), draw 773, 1 seed, window 2030–2034. Ladder the condom-counselling
**coverage** (fraction of treated agents enrolled) ∈ {0, 0.25, 0.5, 0.75,
1.0}; fixed effect `eff=0.5` (50% re-acquisition reduction for ng/ct/tv)
and `dur=6 months`. Mechanism: `cond.CondomCounseling` (mechanism b —
`rel_sus` multiplier on the diagnosed for a window; acquisition only).
Endpoints per rung: CT prevalence (window mean+end), CT incidence, cohort
reinfection /100, mean agents protected.

**Success criteria.** A clean coverage dose-response for CT
reinfection/prevalence, and a like-for-like comparison against the exp 05
PN ladder from the same POC+baseline-PN base. Either (a) condoms drop CT
reinfection materially below what PN scaling achieves → reinfection
prevention is the higher-value lever, or (b) it too plateaus → CT is hard
to shift with any single lever at this draw. Both inform the manuscript's
demand-generation framing.
