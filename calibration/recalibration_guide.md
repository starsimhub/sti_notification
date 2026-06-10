# Recalibration guide

How to redo this calibration. Written assuming the reader was not
involved in the original work.

## When recalibration is required

Recalibrate if **any** of the following is true:

1. **The model has changed** — new disease, new connector, new
   intervention, changed natural-history defaults in STIsim or Starsim
   that affect the disease modules in
   [`../model.py`](../model.py).
2. **STIsim has been upgraded across a minor version** — 1.5 → 1.6,
   etc. Parameter scales are not transferable across minor versions
   (this calibration on 1.5.5 invalidated the prior 1.4 / 1.5.2 fits).
3. **The data has been refreshed** — new ZIMPHIA or DHS round, new
   surveillance window, revised UNAIDS estimates that shift the
   target bands more than the existing 80% CI.
4. **The decision question has changed in a way that requires a
   different target structure** — e.g. age-specific impact at ages
   not currently in the target set.
5. **A structural mechanism has been added** that was not in scope
   here — e.g. a new HIV-coupling biology, an ARV resistance model.

Do *not* recalibrate just because a new minor change to a peripheral
parameter is being investigated — re-running the existing ensemble
under the change is usually the right move.

## Signals the current calibration is no longer valid

- A downstream scenario produces results that contradict the
  acceptance criteria in [`methodology.md`](methodology.md).
- The target bands have moved enough that the ensemble medians no
  longer cover them.
- A reproducibility check (re-running the workflow scripts on the
  saved `draws_used.csv`) fails to reproduce the published figures
  within plotting tolerance.
- Pulling a newer STIsim and re-running 10 randomly-chosen draws from
  `draws_used.csv` shows median results > 20% off the saved
  `ensemble_ts_quantiles`.

The reproducibility check is automated by
[`../calibration/artifacts/scripts/reproduce_check.py`](artifacts/scripts/reproduce_check.py)
(see *Reproduction check* below).

## Prerequisites

### Compute

A multi-core Linux VM on IDM's "Applied Math" Azure subscription
(zebra, gerbil, hedgehog, dugong, paracetherium, agouti120, capybara,
chinchilla120, covaguest, raccoon, woodchuck). Choose worker count
based on shared use:

| Configuration | Wall time (full pipeline) |
|---|---|
| 24 workers (original calibration, 5000 LHS) | ~25h Phase 1 + ~2h Phase 2 + ~30 min figures = ~28h |
| 60 workers (Fix C recalibration, 2000 LHS) | ~45 min Phase 1 + ~25 min Phase 2 + ~12 min figures = ~1.5h |

Smaller LHS (2000 draws on Fix C, vs 5000 in the original) was
viable because the corrected baseline produces a higher Phase 1
sustainability rate (49% vs 35%), so fewer LHS draws are needed to
reach the ~200 robust-draw target. The Fix C cycle produced 169
robust draws — slightly under target, fine for downstream use.

Disk: ~15 GB free for the full intermediate parquet outputs (Phase 1
trajectory data, Phase 2 per-(draw, seed) sims, snapshots).

### Software

- Python 3.11.
- Conda env `starsim` (see global CLAUDE.md for project conda
  conventions in IDM).
- Starsim 3.3.2 (or whatever the current pinned version is).
- STIsim 1.5.5 plus three feature branches required for this
  calibration's mechanics:
  - `feat/partner-notification-network` — `PartnerNotification` API
    used by `SyndromicPN`.
  - `feat/marital-act-decay` — `stable_act_decay` and
    `client_marital_act_mult`.
  - `feat/syph-detectable-state` — `detectable_prevalence` result.

If those have merged into STIsim main, an unpinned editable install
of STIsim main is fine.

```bash
conda activate starsim
pip install -e /path/to/stisim
pip install -e /path/to/starsim
```

### Data

The locked input files in [`../data/`](../data/) are sufficient for
re-running the existing calibration. If recalibration is being
triggered by data refresh, replace those files first and check that
the target bands in `artifacts/scripts/run_ensemble.py` still match
the new data.

### Code inputs

- [`../model.py`](../model.py) — make_sim, network, modules.
- [`../priors.py`](../priors.py) — the 19-parameter calib_pars dict
  and prior bounds.
- [`../interventions.py`](../interventions.py) — ANC ramp,
  symptomatic care-seeking, `SyndromicPN` defaults.

If structural changes have been made to any of these, the prior list
and target bands may need to be re-engineered. See
[`methodology.md`](methodology.md) §"Method evolution".

## Step-by-step reproduction

### 1. Verify the environment

```bash
conda activate starsim
python -c "import stisim, starsim; print(stisim.__version__, starsim.__version__)"
# Expect: 1.5.5 3.3.2 (or current pinned)
```

Smoke-test a single sim using one draw from the saved ensemble:

```bash
cd calibration/artifacts/scripts
python reproduce_check.py --n-draws 1 --n-seeds 1 --n-workers 1
```

Should complete in ~2 minutes. Reports the fraction of (sim, year,
result) points falling outside the saved 95% CI band — expected
~5% by chance, fails if > 15%.

### 2. Re-run the existing ensemble (cheap path — no recalibration)

If the model and data are unchanged and you want to refresh outputs
or verify reproducibility:

```bash
cd calibration/artifacts/scripts
python extract_summary.py --draws-csv ../draws_used.csv \
                          --out-dir reproduced/ \
                          --n-seeds 3 \
                          --n-workers 24
python plot_figures.py --ts-quantiles reproduced/ensemble_ts_quantiles.parquet \
                       --snap-quantiles reproduced/ensemble_snapshots_quantiles.parquet \
                       --fig-dir reproduced/figures/
```

The sims are deterministic given seed; the only divergence sources
are STIsim version drift and host-level numerical differences.
`reproduce_check.py` flags drift above the chance baseline.

### 3. Recalibrate from scratch

Triggered by any of the conditions in *When recalibration is required*.

#### Step 3a — Coverage check on the new model state

Before any LHS work, run a small prior-predictive check (50–200 draws
from the *un-narrowed* prior on the new model) to confirm the data
falls inside the simulated ensemble. The calibration plugin's
[`coverage-check`](https://github.com/InstituteforDiseaseModeling/calib-plugin/tree/main/skills/coverage-check)
skill drives this — invoke it via Claude Code and follow its
discipline.

**Do not proceed to LHS until coverage passes.** If the data is not
bracketed, fix the prior or the model before continuing.

#### Step 3b — Re-engineer priors and targets if needed

Read the per-experiment SUMMARYs on `archive/calibration-2026-06` and
`archive/recalibration-2026-06-fixc` for
the engineering decisions:

- exp 17 / 20 — opening `time_to_undetectable`.
- exp 27 — beta range engineering.
- exp 32 — opening HIV-coupling levers.
- exp 38 — dropping PN priors that were unidentifiable.
- exp 40 — opening marital-decay levers.

The priors in [`../priors.py`](../priors.py) reflect the
end-state of that engineering. If the model has changed, treat
`priors.py` as a starting point, not a fixed input.

#### Step 3c — Run Phase 1 + Phase 2 (LHS + 3-seed robustness)

```bash
cd calibration/artifacts/scripts
python run_ensemble.py --phase all \
                       --out-dir new_run/ \
                       --n-draws 5000 \
                       --seed 45 \
                       --target-size 200 \
                       --n-seeds 3 \
                       --n-workers 24
```

This drives the full pipeline:

1. **Phase 1.** 5000 LHS draws, single-seed each. Filter sustained
   AND `n_pass ≥ 5` → ~200–400 candidates. Outputs:
   - `new_run/phase1_priors.csv`
   - `new_run/phase1_results.jsonl`
   - `new_run/phase1_selection.json`
   - `new_run/phase2_candidates.csv`
2. **Phase 2.** Re-run candidates × 3 seeds, aggregate per-draw
   seed-means, filter sustained 3/3 AND mean `n_pass ≥ 4` →
   ~200 robust draws. Outputs:
   - `new_run/phase2_results.jsonl`
   - `new_run/ensemble_summary.csv`
   - `new_run/draws_used.csv` — the final ensemble.

Expect ~25 hours wall for Phase 1 + ~2 hours for Phase 2 at 24
workers. Phase 1 can be run independently with `--phase 1`; resume
with `--phase 2` once candidates have been inspected.

#### Step 3d — Publication extraction

```bash
python extract_summary.py --draws-csv new_run/draws_used.csv \
                          --out-dir new_run/ \
                          --n-seeds 3
python plot_figures.py --ts-quantiles new_run/ensemble_ts_quantiles.parquet \
                       --snap-quantiles new_run/ensemble_snapshots_quantiles.parquet \
                       --fig-dir new_run/figures/
```

Expect ~30 min wall. Outputs:
- `new_run/ensemble_ts_quantiles.parquet`
- `new_run/ensemble_snapshots_quantiles.parquet`
- `new_run/figures/*.png` — 5 publication figures.

Pass `--keep-raw` to `extract_summary.py` if you also want the
per-(draw, seed) `time_series.parquet` and `snapshots.parquet`
(~12 MB total).

## Validation and sign-off

A recalibration is **accepted** when:

1. The reproducibility check passes against the new ensemble itself
   (i.e. results are deterministic given the saved draws + seeds).
2. The ensemble passes the four acceptance criteria from
   [`methodology.md`](methodology.md): HIV in band, HIV+/HIV− syph
   ratio in band, syph stage shares plausible, NG median in band.
3. Per-target results are documented in a recalibration `SUMMARY.md`
   following the `experiment-close` skill conventions.
4. The new `draws_used.csv` + quantile parquets + figures replace
   the contents of `calibration/artifacts/` via a PR to main,
   *not* by direct overwrite. The previous calibration's artifacts
   stay on the previous tagged release.

If the recalibration finds that the structural ceilings from this work
(syph absolute prev; CT under-calibration) have moved, that's a
significant finding — write it up in the SUMMARY and propose
manuscript-level revisions.

## What not to bother retrying

These were tried during the original calibration and found not to
work. Don't re-explore unless the model has structurally changed.

- **Widening the syph beta prior below 0.10.** Beta is not the
  bottleneck — network and natural-history are.
- **Exogenous case imports as an extinction guard.** Imports collapse
  the bifurcation onto the hot branch; results lose decision relevance.
- **Latent-stage half-life manipulation as a way to lower absolute
  prev.** Independent of the natural-history value chosen, the
  minimum-sustaining FOI sets the equilibrium prev.
- **`rel_trans_primary = 5`.** Fragile; 2/3 seeds collapse.
- **FSW MF-concurrency multiplier as a syph absolute-prev lever.**
  Zero correlation with non-trep_f outcomes (exp 33).
- **Marital coital-decay as an absolute-prev lever.** Identifiable but
  compensated for (exp 40).

The structural ceiling on syph absolute prev is genuinely hard. Three
independent structural attempts confirmed it. The right move for the
manuscript is to frame syph results as relative-effect contrasts.

## Reproduction check

`artifacts/scripts/reproduce_check.py` is the canonical "is the
calibration still valid" test. It:

1. Loads `artifacts/draws_used.csv`.
2. Randomly samples N draws (default 10).
3. Runs each at K seeds (default 3).
4. Compares each resulting (sim, year, result) point against the
   saved 95% CI band in `ensemble_ts_quantiles.parquet`. Exits 0
   if the violation rate is ≤ `--max-violation-rate` (default 15%,
   versus a ~5% baseline by chance), 1 otherwise.

Run it monthly during the scenario-analysis phase and any time
STIsim or Starsim is upgraded.
