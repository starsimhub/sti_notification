# Instructions for the VM agent: exp 07 recalibration + factorial rerun

**Branch:** `reframe/no-syph-fp-harms`. Work only on this branch. Never commit to `main`.
**Owner:** Robyn Stuart. Report back to her at each checkpoint marked 🛑. Do not continue past a 🛑 if its pass criteria fail.

## 0. Context (read first)

This branch reorients the manuscript (`docs/sti_manuscript_v2.md`) around one question: what share of index cases and partner notifications (PN) are triggered by false-positive POC results, and how does that share change as demand-side interventions succeed? `docs/submission_plan.md` has the background.

Changes made on this branch (24 Nov 2026), **none of which has been executed yet**:

- **Syphilis removed** from `model.py`, `interventions.py`, `connectors.py`, PN and the scenario driver. `make_sim()` ignores legacy syph kwargs with a warning.
- **`interventions.py`**:
  - POC specificity is 98% by default and can be overridden through `make_sim(poc_spec=...)`, as a scalar or `{disease: [F, M]}`.
  - `CondomCounseling` defaults to eff=0.30, covering NG/CT/TV only.
  - `CareSeekScaler` now also scales BV care-seeking. SimpleBV's `p_symp_care` is an `ss.bernoulli`; the code handles this via `Dist.set(p=...)`.
- **`analyzers.PresenterEtiology`**: an `ss.Intervention` inserted before the detection modules (in `model.make_interventions`). It records NG/CT/TV status among care-seekers and PN attendees.
- **`scenarios.py`**: re-anchored ladders plus `SPEC_SWEEP` and `SPEC_SWEEP_CELLS`.
- **`run_scenarios.py`**:
  - 83 cells: SOC, 64 POC cells at 98% specificity, and 18 specificity-sweep cells.
  - New `spec` column.
  - Defaults to exp 07 draws and `N_AGENTS=20000`.
- **`experiments/07_2026-11-24_no_syph_calibration/run.py`**: the new calibration.
- **`analysis/fp_harms.py`**: tables and figures for the reframed paper.
- **`process_results.py`**: syphilis dropped; `spec` added to the grouping.

## 1. Setup

```bash
cd ~/sti_notification            # adjust to the VM checkout path
git fetch origin
git checkout reframe/no-syph-fp-harms
git pull --ff-only
conda activate starsim
python -c "import stisim, starsim; print(stisim.__version__, starsim.__version__)"
```

**Expected:** stisim 1.5.7 and starsim 3.3.2. If the versions differ, 🛑 stop and report. Do not upgrade.

Use `nproc` to choose `N_WORKERS`: leave about 4 cores free.

## 2. Smoke tests 🛑

Run each of these and record wall time and output.

### 2a. Model builds and runs
```bash
python model.py
```
**Pass:**
- Prints the diseases `['hiv', 'ng', 'ct', 'tv', 'bv']`. No `syph` or `gudp` modules, and no syph connectors.
- Prints a finite HIV prevalence.

### 2b. Interventions wire correctly (write as `scratch/check_wiring.py`, don't commit)
```python
import numpy as np, starsim as ss
from model import make_sim
from interventions import CareSeekScaler, CondomCounseling, PNIntensitySwitch
from scenarios import PN_INTENSITY

for poc in (None, True):
    sim = make_sim(seed=1, n_agents=5000, start=1985, stop=2030, poc=poc,
                   poc_spec=0.98 if poc else None, fetal_health=False, verbose=-1)
    sim.pars['interventions'] = list(sim.pars['interventions']) + [
        CareSeekScaler(mult=1.75, start=2027),
        PNIntensitySwitch(**PN_INTENSITY['high'], start=2027),
        CondomCounseling(coverage=0.5, start=2027)]
    sim.run()
    names = list(sim.interventions.keys())
    print('poc', poc, names)
    assert 'presenter_etiology' in names and names.index('presenter_etiology') < names.index('syndromic_vds')
    pe = sim.interventions.presenter_etiology.results
    print('  care presenters F (sum):', pe['n_care_f'].values.sum(), ' NG/CT+:', pe['ngct_care_f'].values.sum())
    print('  pn presenters (sum):', pe['n_pn_f'].values.sum() + pe['n_pn_m'].values.sum())
    print('  bv p_symp_care after 2027:', sim.diseases.bv.pars.p_symp_care.pars.p)   # expect 0.3*1.75=0.525
    print('  ng p_symp_care after 2027:', sim.diseases.ng.pars.p_symp_care)          # expect ~[0.8575, 1.0]
    if poc:
        print('  panel spec:', sim.interventions.panel.pars.spec)                     # expect 0.98
```
**Pass:**
- `presenter_etiology` runs before `syndromic_vds`.
- Presenter counts are greater than 0, and NG/CT-positive counts are below the presenter counts.
- BV `p_symp_care.p` is about 0.525.
- Panel specificity is 0.98.

If `CareSeekScaler` fails on BV, fix it minimally in `interventions.py`. For example, `SimpleBV` may store `p_symp_care` differently: inspect `stisim/diseases/bv.py`. Then rerun.

### 2c. SOC and POC are identical before 2027
Run SOC and POC (no levers) with the same seed to 2030. Compare annual `ng.prevalence` and `ct.prevalence` for 1985–2026.

**Pass:** identical before 2027. A difference means intervention ordering or start gating is broken: 🛑 stop and report.

### 2d. Calibration smoke
```bash
N_DRAWS=4 K_SEEDS=2 N_AGENTS=5000 STOP=2026 N_WORKERS=8 \
  python experiments/07_2026-11-24_no_syph_calibration/run.py
```
**Pass:**
- 8/8 sims ok.
- `outputs/per_draw_means.csv` has finite values for all 7 targets.
- `ng_new_inf_per_yr` etc. are of order 10^5–10^6 per year, not per month.

If the incidence units look 12× off, check `_stat(..., 'annual_sum')`.

Then delete the smoke outputs: `rm -rf experiments/07_*/outputs`.

### 2e. Scenario smoke (after 3b produces draws_used.csv, or point DRAWS at a smoke file)
```bash
SMOKE=1 N_WORKERS=30 python run_scenarios.py
```
**Pass:**
- 125/125 ok.
- `results/scenarios_smoke.kavg.csv` has a `spec` column, `pres_*` columns and no `syph_*` columns.

🛑 **Report to Robyn:** smoke results and timing per sim at 20k agents. Use the timing to estimate the full runtimes in sections 3 and 4.

## 3. Exp 07 calibration

### 3a. Timing check
Estimate the runtime as 500 draws × 5 seeds × (time per sim at 20k agents to 2030) ÷ N_WORKERS. If it is over about 12 h, 🛑 ask Robyn whether to drop to `N_AGENTS=15000` or 300 draws.

### 3b. Full run
```bash
nohup env N_DRAWS=500 N_WORKERS=<n> python \
  experiments/07_2026-11-24_no_syph_calibration/run.py \
  > experiments/07_2026-11-24_no_syph_calibration/outputs_run.log 2>&1 &
```
(Run it inside `tmux` or with `nohup` so it survives disconnects.)

### 3c. Acceptance checks 🛑
From the run log or `outputs/per_draw_means.csv`:

- **At least 30 acceptable draws.** If fewer:
  1. Rerank only (no rerun) with `ACCEPT_TOL=1.0`. Write a tiny `rerank.py` modelled on exp 06's that imports `score` from `run.py` and reads `results_raw.jsonl`.
  2. If still under 30, 🛑 report: list which targets fail most often (`dist_*` columns) and the prior ranges of the failing parameters.
- **Spread across retained draws.** For each prevalence target, max/min should be within about 2.5× (exp 06 had 100×+ for CT). Report the min/median/max table that the script prints.
- **Sustainability.** `min_seeds_sustained == 5` for most retained draws.

Then:
- Write `experiments/07_2026-11-24_no_syph_calibration/SUMMARY.md` in the exp 06 format: question, method, result, target table with bands, retained-draw spread, findings, caveats.
- Make an epi overview figure. Adapt `exploratory/plot_epi.py` or exp 06's `plot_epi.py` to read `outputs/timeseries.parquet`, and overlay the data from `data/zimbabwe_sti_data.csv` and `data/zimbabwe_hiv_calib.csv`.
- **Validation (record, don't fit):** STICH 2020–21 ages 16–24: CT 14.7%, NG 2.8%. The script records `ng_prev_15_25_2021` and `ct_prev_15_25_2021`. Report the model median and IQR against these.

Commit:
```bash
git add experiments/07_2026-11-24_no_syph_calibration/{run.py,SUMMARY.md,*.png} \
        experiments/07_2026-11-24_no_syph_calibration/outputs/{draws_used.csv,per_draw_means.csv,priors.csv}
git commit -m "exp 07: syphilis-free calibration (N accepted, top-30 retained)"
git push
```
Do **not** commit `results_raw.jsonl` or `timeseries.parquet` if they are over about 20 MB.

## 4. Factorial + specificity sweep

### 4a. Runtime
83 cells × N_DRAWS × 5 seeds. Start with `N_DRAWS=30`. If the estimate is over about 24 h, use `N_DRAWS=20` and tell Robyn.

```bash
nohup env N_DRAWS=30 N_SEEDS=5 N_WORKERS=<n> python run_scenarios.py \
  > results/scenarios_run.log 2>&1 &
```

### 4b. Checks 🛑
- All sims ok (`err=0` in the log). If errors occur, report the first 10 messages.
- **Sanity:**
  - The SOC cell's 2015–25 prevalence matches the exp 07 calibration medians within noise.
  - POC-alone averts more than 0% of infections in most draws.
  - `fp_share_f` = `pn_new_index_no_sti_f / pn_new_index_total_f` should rise across POC cells with intensity and fall with specificity.

  **Report whatever you find, including if it doesn't behave this way. Do not tune anything to make it behave.**

### 4c. Post-processing
```bash
python process_results.py
python analysis/fp_harms.py
```
**Outputs:**
- `results/fp_cells.csv`, `results/fp_spec_sweep.csv`, `results/shapley.csv`
- `figures/fig_fp_mechanism.png`, `figures/fig_harm_benefit.png`

Look at both figures. In Fig 5A, the points should lie near the analytic curves; systematic deviation is a finding to report, not a bug to hide.

### 4d. Update plotting scripts
These scripts still reference syphilis and must be updated to drop it:
- `plotting/plot_slide3.py`, `plot_slide5.py`, `plot_slide6.py`, `plot_slide12.py`, `plot_slide13.py`
- `plotting/compute_slide4_ppv.py`, `plotting/plot_result1.py`
- `exploratory/plot_epi.py`, `dashboard/index.qmd`

For each one: remove syphilis panels and columns, filter to `spec == 0.98` or SOC where the script assumes one value per cell, and rename "bundled prevention" to "condom counselling" in labels. The manuscript Figures 2, 3 and 4 come from `plot_slide4_etiology` (rebuild), `plot_slide5` and `plot_slide12` respectively. Add a Shapley inset to `plot_slide12` from `results/shapley.csv`.

### 4e. Commit
```bash
git add results/scenarios.kavg.csv results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet \
        results/fp_*.csv results/shapley.csv figures/*.png plotting/ exploratory/plot_epi.py dashboard/index.qmd
git commit -m "exp 07 factorial + spec sweep: results, FP-harms analysis, figures"
git push
```
Never commit `raw_results/`; it is gitignored.

## 5. Report back 🛑

Post a short report covering:

1. Calibration: number of acceptable draws, the retained-draw spread table, and the validation numbers.
2. Headline numbers to fill the [XX] values in `docs/sti_manuscript_v2.md`, each as median (IQR):
   - % infections averted: POC alone; all moderate; all high.
   - Shapley shares at high intensity.
   - Female false-positive share: SOC; POC alone; all high, at each specificity.
   - Presenter NG/CT prevalence: POC alone vs all high.
   - Unnecessary notifications per year.
   - The minimum specificity that keeps the all-high false-positive share at or below the POC-alone level at 98%.
3. Anything surprising, or anything that contradicts the manuscript's framing.
4. Compute used.

Do **not** edit `docs/sti_manuscript_v2.md` numbers yourself unless Robyn asks; send her the table.

## Don'ts
- Don't change model parameters, priors, ladders or targets without asking. Report and wait instead.
- Don't merge into `main`, force-push or rewrite history.
- Don't upgrade stisim or starsim.
- Don't delete exp 01–06 outputs.
