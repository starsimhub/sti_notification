# Exp 05 — PN intensity ladder (+ EPT), POC arm

**Question.** Exp 04 showed CT reinfection is driven by the index's own
concurrent regular partners going *undertreated* — a coverage gap PN can
in principle close (mean partners notified rose 0.19→0.69 from SOC→PN×3,
reinfections fell 52→45). So: **how far does scaling PN coverage upward
push CT reinfection and prevalence — does it keep improving, or plateau
below meaningful impact (reinfection-limited)?** And: is the binding leak
*notification* or *attendance* — i.e. does EPT (treat every notified
partner, no clinic visit required) add beyond notification scaling?

**Plan.** POC etiological arm, draw 773, 1 seed (seeds/ensemble later),
window 2030–2034. A ladder of PN coverage multipliers on the baseline
edge-stratified notify+attend rates (attendance cap raised to 0.99 so the
ladder isn't clipped early):

- `pn ×0` (no PN), `×1` (baseline), `×2`, `×3`, `×5`, `×8`
- `EPT`: notify at ×5 but **attend → 1.0** (every notified partner is
  treated without attending) — isolates the attendance leak.

Endpoints per rung: CT prevalence (window mean + end), CT new infections
(window), cohort reinfection /100, PN partners notified/attending, mean
concurrent partners notified per index. Reuses exp 04's `STIChainTracer`.

**Success criteria.** A clean dose-response. Three informative shapes:
(a) keeps falling with PN → coverage is the lever, push it; (b) plateaus
early well above zero → reinfection-limited, PN alone insufficient,
motivating condoms (exp 06); (c) EPT lands well below the same-notify
ladder rung → attendance is the binding leak and EPT is worth it. Any of
these is a useful result.
