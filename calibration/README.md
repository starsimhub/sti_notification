# Calibration record

This directory is the institutional record of the STIsim Zimbabwe joint
calibration (HIV + syphilis + NG + CT + TV) carried out between
March–June 2026 in support of the partner-notification (PN) and
care-seeking decision analysis.

It is documentation, not an active workspace. The development branch
where the calibration was actually performed is preserved as an
archival artefact (see [Provenance](#provenance) below); this folder
contains only the durable outputs and the knowledge required to
understand, defend, or reproduce them.

## Contents

| File | Purpose |
|---|---|
| [`calibration_summary.md`](calibration_summary.md) | Executive summary: objectives, decisions, findings, what was adopted, why. |
| [`methodology.md`](methodology.md) | Detailed methodology: data, model, parameters, method evolution, acceptance criteria. |
| [`assumptions.md`](assumptions.md) | Fixed assumptions, structural limitations, known risks. |
| [`recalibration_guide.md`](recalibration_guide.md) | When to recalibrate, and how — step-by-step. |
| [`artifacts/`](artifacts/) | The 200-draw parameter ensemble, ensemble quantile summaries, publication figures, and the scripts that reproduce them. |

Start with `calibration_summary.md` for the headline result. Read
`recalibration_guide.md` if the question is "do we need to redo this?"
or "how would I redo this?"

## What landed on main from this work

- Final model code: [`model.py`](../model.py),
  [`priors.py`](../priors.py),
  [`interventions.py`](../interventions.py).
- Locked input data: [`data/`](../data/).
- The 200-draw posterior ensemble: `artifacts/draws_used.csv` +
  ensemble quantile parquets.
- Five publication figures used in the manuscript: `artifacts/figures/`.
- The three workflow scripts that take `draws_used.csv` →
  per-sim results → ensemble quantiles → figures, in
  `artifacts/scripts/`.

What did not land: the 41-experiment development history, ~290 MB of
intermediate parquets/CSVs/figures, and the dead-end branches. Those
are preserved on the archival branch (see below).

## Provenance

The calibration was developed on branch `calibration/zimbabwe` across
41 numbered experiments under `experiments/`. After the final
ensemble was produced and the publication figures regenerated (exp 40
and exp 41), that branch was tagged `archive/calibration-2026-06` and
preserved as a historical artefact. Future development should not
merge or extend it; any recalibration starts from `main` per
[`recalibration_guide.md`](recalibration_guide.md).

To inspect the full development history:

```bash
git checkout archive/calibration-2026-06
ls experiments/
```

Each `experiments/NN_*/SUMMARY.md` is the per-experiment record at
the time of that experiment's close. They are immutable.
