# Exp 30 — Definitive LHS sweep over 14 priors

**Date opened:** 2026-06-07.

**Question.** With all the structural fixes now in place — the
SyphTx-clears-nontrep patch, the trep BoolState with window-period
+ 80% persistence, dur_early 22-24mo, rel_trans_primary as a
calibration knob, defensible ANC ramp, boosted FSW care-seeking CSV
— **does ANY configuration in our 14-dim prior space produce
reasonable concentrated-sustained syph dynamics**?

This is the **definitive** test. After many hand-picks and
single-parameter sweeps, the question is whether the model can
hit the loose target band anywhere in its prior support. A null
result here means we accept the relaxed-relaxed calibration and
move on to decision analysis. A positive result gives us a
concrete configuration to feed HM.

**Why now.** All known model bugs and structural improvements are in:

| Fix | Where | Commit |
|---|---|---|
| `nontrep` / `trep` result naming | stisim syphilis.py | exp 27 |
| SyphTx clears nontrep within 6-12mo of early-stage treatment | stisim syph_interventions.py | exp 28 |
| dur_early extended 12-14mo → 22-24mo | stisim syphilis.py | exp 29 |
| `rel_trans_primary` opened as calibration param | sti_notification priors.py | exp 29 |
| `trep` BoolState distinct from ever_exposed; 80% persists for life; window-period treatment clears trep | stisim syphilis.py + syph_interventions.py | (this morning) |
| Defensible ANC ramp default (peak 0.70 by 2018) | sti_notification interventions.py | exp 28 |

Plus testing/treatment pipeline audit (this morning) confirmed both
syndromic + ANC dx → tx pipeline works correctly (882 dx → 880 tx,
1:1).

**Plan.**

- **300 LHS draws** across the 14-dim prior in `priors.py`.
- **Single seed per draw** (`seed = draw_idx * 1000`).
- 10k agents, 1985-2040, 24 workers, ~10-15 min wall clock.
- Same boosted care-seeking CSV (exp 24's), defensible ANC ramp.
- Capture: standard summary metrics + by-stage transmission shares
  per [[feedback-stage-share-check]] + FSW prev + client prev +
  full series.

**Success criteria.**

Loose targets ([[project-syph-calibration-state]]):

| Target | Range |
|---|---|
| FSW prev 2019 | [0.20, 0.40] |
| nontrep_f 2016 | [0.01, 0.03] |
| trep_f 2016 | [0.05, 0.10] |
| Primary stage share (plateau) | [0.45, 0.65] |
| Secondary stage share (plateau) | [0.25, 0.45] |
| Early latent stage share (plateau) | ≤ 0.15 |
| Sustained to 2040 | new_inf > 0, prev_f ≥ 0.001 |

A **definitive pass** = at least 5 draws bracketing all 7 targets.

A **partial pass** = at least 1 draw passes 6/7 targets. Document
which target is the hardest miss; that determines what fix is
needed next.

A **definitive miss** = no draw gets to 6/7. Means model
architecture genuinely cannot produce realistic dynamics; accept
exp 28's hand-pick + relaxed calibration as the baseline; move to
decision analysis.

**Decision branches.**

- **Definitive pass** → open exp 31 = tight LHS coverage check
  (~100 draws) around the passing region + start HM.
- **Partial pass** → understand the miss, decide whether to push.
- **Definitive miss** → end calibration phase. Accept exp 28 as
  the baseline, document the scale mismatch in the paper, and
  switch to decision analysis on PN interventions.

**What this experiment does NOT do.**

- Does not run HM.
- Does not add more parameters beyond the existing 14.
- Does not change interventions or network architecture.
- Does not use multiple seeds per draw (one seed each — broad
  exploration over single-realization noise).
