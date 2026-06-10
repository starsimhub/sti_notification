# Calibration record

This directory is the institutional record of the STIsim Zimbabwe joint
calibration (HIV + syphilis + NG + CT + TV) carried out between
March–June 2026 in support of the partner-notification (PN) and
care-seeking decision analysis. The current published baseline is a
**169-draw posterior ensemble** produced after a structural correction
to the syph syndromic-dx baseline ("Fix C", PR #5) on a fresh
recalibration cycle.

It is documentation, not an active workspace. Both the original
development branch and the post-Fix-C recalibration cycle are preserved
as archival artefacts (see [Provenance](#provenance) below); this folder
contains only the durable outputs and the knowledge required to
understand, defend, or reproduce them.

## Contents

| File | Purpose |
|---|---|
| [`calibration_summary.md`](calibration_summary.md) | Executive summary: objectives, decisions, findings, what was adopted, why. |
| [`methodology.md`](methodology.md) | Detailed methodology: data, model, parameters, method evolution, acceptance criteria. |
| [`assumptions.md`](assumptions.md) | Fixed assumptions, structural limitations, known risks. |
| [`recalibration_guide.md`](recalibration_guide.md) | When to recalibrate, and how — step-by-step. |
| [`artifacts/`](artifacts/) | The 169-draw parameter ensemble, ensemble quantile summaries, publication figures, and the scripts that reproduce them. |

Start with `calibration_summary.md` for the headline result. Read
`recalibration_guide.md` if the question is "do we need to redo this?"
or "how would I redo this?"

## What landed on main from this work

- Final model code with Fix C two-channel syndromic syph dx:
  [`model.py`](../model.py), [`priors.py`](../priors.py),
  [`interventions.py`](../interventions.py).
- Locked input data: [`data/`](../data/).
- The **169-draw posterior ensemble** on Fix C:
  `artifacts/draws_used.csv` + ensemble quantile parquets.
- Five publication figures used in the manuscript: `artifacts/figures/`.
- The workflow scripts that take `draws_used.csv` → per-sim results
  → ensemble quantiles → figures, in `artifacts/scripts/`.

What did not land: 44 numbered experiments worth of development
history (41 from the original cycle + 3 from the Fix C recalibration),
intermediate parquets/CSVs/figures, dead-end branches. Those are
preserved on the two archival tags (see below).

## Provenance

Two archival cycles preserved as tags:

| Tag | What it contains | When tagged |
|---|---|---|
| `archive/calibration-2026-06` | Branch `calibration/zimbabwe`: 41 experiments, original calibration pipeline. Used the (later-discovered-as-incorrect) `gud` dx product for syph syndromic management. Produced a 200-draw ensemble that was on `main` briefly before being superseded. | 2026-06-09 |
| `archive/recalibration-2026-06-fixc` | Branch `recalibration/zimbabwe-2026-06`: 3 experiments (coverage check, full 2000-draw recalibration, publication figures) on the Fix C corrected baseline. Produced the **current published 169-draw ensemble**. | 2026-06-10 |

Future development should not merge or extend either archival branch;
any recalibration starts from `main` per
[`recalibration_guide.md`](recalibration_guide.md).

To inspect the full development history:

```bash
# Original calibration cycle
git checkout archive/calibration-2026-06
ls experiments/

# Fix C recalibration cycle
git checkout archive/recalibration-2026-06-fixc
ls experiments/
```

Each `experiments/NN_*/SUMMARY.md` is the per-experiment record at
the time of that experiment's close. They are immutable.
