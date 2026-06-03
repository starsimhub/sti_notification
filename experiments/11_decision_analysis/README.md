# Exp 11 — Decision analysis: PN and care-seeking impact thresholds

**Question.** What levels of partner notification coverage and
care-seeking intensity produce meaningful health impact (infections
averted, adverse birth outcomes averted)?

**Motivation.** Exp 10 produced a 500-draw posterior ensemble (ESS=75.6).
This experiment propagates that posterior through the three scenario
sweeps defined in ANALYSIS_PLAN.md:

1. **PN coverage sweep** — none / low / med / high (baseline care-seeking)
2. **Care-seeking sweep** — 1.0x / 1.25x / 1.5x / 2.0x (PN=med)
3. **Dx × PN interaction** — SOC vs POC × 4 PN levels

**Plan.** 50 weighted-resampled posterior draws × 17 scenarios (1
baseline + 16 sweep cells) = 850 sims at 10k agents, 1985–2030.
For each posterior draw, compute scenario − baseline differences to
get impact distributions. Plot threshold curves.

**Success criteria.** Clear dose-response for at least one sweep axis.
Uncertainty bands narrow enough to identify meaningful thresholds.
