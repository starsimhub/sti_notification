# 01_coverage_check

Prior predictive coverage check for the Zimbabwe calibration.

## Question

Does the model — under the priors defined in `priors.py` — produce
trajectories that visually **bracket every calibration target**? Coverage
failure means the prior is too narrow, the model is misspecified, or
both, and is a blocker for any subsequent calibration wave.

## What it does

1. `run.py` samples N draws from the eight calibration parameters
   (HIV/syph/NG/CT/TV β + 2 network parameters + HIV `rel_init_prev`),
   uniform or log-uniform per `priors.py`.
2. For each draw it builds a fresh sim (`make_sim`, n_agents=5k,
   1985–2025, no PN, no FetalHealth — coverage is only about the
   disease-prevalence axis), applies the parameter draw via
   `sti.calibration.set_sim_pars`, runs, extracts the 5 prevalence
   trajectories we calibrate against.
3. `plot.py` draws every trajectory in light grey and overlays the
   real data points.

## How to run

```bash
# Local sanity check (10 draws, single core, ~few min)
cd experiments/01_coverage_check
python run.py
python plot.py

# IDM Azure VM (100 draws, 75 cores)
# edit run.py: N_DRAWS=100, N_WORKERS=75
python run.py
python plot.py
```

## Outputs

- `results/coverage_dfs.obj` — list of per-draw result dataframes
- `results/coverage_draws.obj` — list of parameter-draw dicts
- `figures/coverage.png` — 5 trajectory panels with data overlay (one
  per target)

## Read this after the run

Write up findings in `SUMMARY.md`:
- For every panel: do trajectories bracket the data points?
- For any panel where they don't: is the prior too narrow (widen),
  too wide (run more draws), or is the model unable to reach the
  observed range (model misspecification — escalate before continuing)?
- Any unexpected dynamics (extinction, blow-ups)?

Coverage passing → handoff to `method-selection` for the formal HM
choice and `parameter-engineering` for parameter pruning before the
first HM wave (`02_*`).
