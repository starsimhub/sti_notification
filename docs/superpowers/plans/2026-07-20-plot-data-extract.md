# Plot-Data Extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `results/` 100% committable by moving the fat factorial outputs to a new gitignored `raw_results/` and generating slim plot-only slices in `results/`.

**Architecture:** Two roles previously conflated in `results/` are split. `run_scenarios.py` writes its fat outputs (`.jsonl`, full TS + snapshot parquets) to `raw_results/` (gitignored, VM-only) and its small K-avg CSV to `results/` (committable). A new `build_plot_data.py` reads the fat parquets and produces slim versions in `results/` filtered to the exact `(cell × result_name × disease)` slice consumed by the 8 committed slide plots + `figures/supplementary/fig_epi_overview.png`. Plot scripts for the 8 slides and `fig_epi_overview` need zero edits (slim files land at the same paths they already read). Three exploratory scripts get one-line path constant updates.

**Tech Stack:** Python 3, pandas, pyarrow (parquet), starsim conda env.

## Global Constraints

- Everything in `results/` must be safe to commit. Anything larger than a low six-figure byte count belongs in `raw_results/`.
- The slim `results/scenarios_timeseries.parquet` must contain exactly the cells listed in `PLOT_CELLS` (11 cells: SOC + 10 POC arms across slides 6/9/10/11), the result_names in `PLOT_RESULTS` (4), and the diseases in `PLOT_DISEASES` (5).
- The slim `results/scenarios_snapshots.parquet` must contain only `cell == 'SOC'` and `year == 2027`.
- The 8 `figures/fig_slide*.png` plots + `figures/supplementary/fig_epi_overview.png` must run against the slim `results/` with zero source edits.
- No test infrastructure exists in this repo (no `tests/`, no `pytest.ini`). Verification is done by running the deliverable script and asserting on its output — not by writing separate test files.
- Conda env: `starsim`. Activate with `conda activate starsim` before running any Python.

---

### Task 1: Create `raw_results/` and gitignore it

**Files:**
- Create: `raw_results/.gitkeep` (empty file so the directory can exist in git for readers without breaking the ignore rule)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: (nothing)
- Produces: `raw_results/` directory (gitignored except for `.gitkeep`) — Task 2 uses it as the destination for `git mv`.

- [ ] **Step 1: Read current `.gitignore` to find the right insertion point**

Run: `cat .gitignore`

Expected: shows the current ignore rules (likely includes `results/*.parquet` or similar).

- [ ] **Step 2: Add `raw_results/` to `.gitignore`**

Edit `.gitignore` — append at the end (or in the appropriate section if there's a clear "outputs" section):

```
# Fat factorial outputs from run_scenarios.py — see docs/superpowers/specs/2026-07-20-plot-data-extract-design.md
raw_results/
!raw_results/.gitkeep
```

- [ ] **Step 3: Create the directory with a keeper file**

Run:
```bash
mkdir -p raw_results
touch raw_results/.gitkeep
```

- [ ] **Step 4: Verify git sees only `.gitkeep`, not other contents**

Run:
```bash
ls -la raw_results/
git status raw_results/ .gitignore
```

Expected: `.gitkeep` is untracked, `.gitignore` is modified. If you have leftover files in `raw_results/` from earlier, they should NOT show up in `git status`.

- [ ] **Step 5: Commit**

```bash
git add .gitignore raw_results/.gitkeep
git commit -m "chore: add gitignored raw_results/ for fat factorial outputs"
```

---

### Task 2: Migrate existing fat files from `results/` to `raw_results/`

**Files:**
- Move: `results/scenarios.jsonl` → `raw_results/scenarios.jsonl`
- Move: `results/scenarios_timeseries.parquet` → `raw_results/scenarios_timeseries.parquet`
- Move: `results/scenarios_snapshots.parquet` → `raw_results/scenarios_snapshots.parquet`
- Move (if present): `results/scenarios_smoke.jsonl`, `results/scenarios_smoke_timeseries.parquet`, `results/scenarios_smoke_snapshots.parquet`

**Interfaces:**
- Consumes: `raw_results/` directory from Task 1.
- Produces: fat parquets available at `raw_results/*.parquet` for Task 4's `build_plot_data.py` to read.

- [ ] **Step 1: Snapshot current state before touching git**

Run:
```bash
git ls-files results/ | grep -E '(parquet|jsonl)$'
ls -la results/scenarios*.parquet results/scenarios*.jsonl 2>&1
```

Expected: git shows which fat files are tracked (from earlier session, `scenarios_timeseries.parquet` and `scenarios_snapshots.parquet` are tracked with M status). The `ls` output shows what's physically present.

- [ ] **Step 2: Un-track the currently-tracked fat parquets without deleting the working copies**

Run:
```bash
git rm --cached results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet
```

Expected: git reports two files staged for deletion from the index. Working copies remain on disk.

- [ ] **Step 3: Move fat files to `raw_results/`**

Run:
```bash
mv results/scenarios.jsonl raw_results/ 2>/dev/null || true
mv results/scenarios_timeseries.parquet raw_results/
mv results/scenarios_snapshots.parquet raw_results/
mv results/scenarios_smoke.jsonl raw_results/ 2>/dev/null || true
mv results/scenarios_smoke_timeseries.parquet raw_results/ 2>/dev/null || true
mv results/scenarios_smoke_snapshots.parquet raw_results/ 2>/dev/null || true
```

- [ ] **Step 4: Verify results/ no longer has fat files and raw_results/ has them**

Run:
```bash
ls -la results/scenarios*.parquet results/scenarios*.jsonl 2>&1 | grep -v cannot || echo "results/ clean"
ls -la raw_results/
```

Expected: results/ shows no scenarios*.parquet or scenarios*.jsonl (kavg.csv is still there and that's correct). raw_results/ shows the moved files plus `.gitkeep`.

- [ ] **Step 5: Commit**

```bash
git add -u results/
git commit -m "chore: move fat factorial outputs from results/ to raw_results/

The two tracked parquets get un-tracked via git rm --cached; working
copies moved on disk to raw_results/ (gitignored)."
```

Expected: commit succeeds; `git status results/` shows only the K-avg CSV and other small committable files.

---

### Task 3: Route `run_scenarios.py` outputs — fat to `raw_results/`, K-avg to `results/`

**Files:**
- Modify: `run_scenarios.py:58` (OUT constant + new RAW_OUT)
- Modify: `run_scenarios.py:312` (mkdir)
- Modify: `run_scenarios.py:317-319` (full-run output paths)
- Modify: `run_scenarios.py:335-337` (smoke output paths)
- Modify: `run_scenarios.py:394` (K-avg CSV path — currently derived from `outfile.with_suffix`, must be explicitly routed to `OUT`)

**Interfaces:**
- Consumes: `raw_results/` directory from Task 1.
- Produces: `run_scenarios.py` that writes jsonl/ts/snap parquets to `raw_results/` and K-avg CSV to `results/`. Downstream `build_plot_data.py` (Task 4) reads from `raw_results/`.

- [ ] **Step 1: Read the current top-of-file constants**

Run: `sed -n '55,62p' run_scenarios.py`

Expected: shows `OUT = REPO / 'results'` near line 58.

- [ ] **Step 2: Add `RAW_OUT` constant next to `OUT`**

Edit `run_scenarios.py` at line 58, replacing:
```python
OUT = REPO / 'results'
```
with:
```python
OUT = REPO / 'results'          # small, committable aggregates (kavg CSV)
RAW_OUT = REPO / 'raw_results'  # fat VM-only outputs (jsonl, full TS/snap parquets)
```

- [ ] **Step 3: Add `RAW_OUT.mkdir` next to the existing `OUT.mkdir`**

Find the line `OUT.mkdir(parents=True, exist_ok=True)` (around line 312) and change to:
```python
    OUT.mkdir(parents=True, exist_ok=True)
    RAW_OUT.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Route full-run jsonl/ts/snap paths to `RAW_OUT`**

Find (around lines 317–319):
```python
    outfile = OUT / 'scenarios.jsonl'
    ts_parquet = OUT / 'scenarios_timeseries.parquet'
    snap_parquet = OUT / 'scenarios_snapshots.parquet'
```
Change to:
```python
    outfile = RAW_OUT / 'scenarios.jsonl'
    ts_parquet = RAW_OUT / 'scenarios_timeseries.parquet'
    snap_parquet = RAW_OUT / 'scenarios_snapshots.parquet'
```

- [ ] **Step 5: Route smoke jsonl/ts/snap paths to `RAW_OUT`**

Find (around lines 335–337, inside the `if smoke:` block):
```python
        outfile = OUT / 'scenarios_smoke.jsonl'
        ts_parquet = OUT / 'scenarios_smoke_timeseries.parquet'
        snap_parquet = OUT / 'scenarios_smoke_snapshots.parquet'
```
Change to:
```python
        outfile = RAW_OUT / 'scenarios_smoke.jsonl'
        ts_parquet = RAW_OUT / 'scenarios_smoke_timeseries.parquet'
        snap_parquet = RAW_OUT / 'scenarios_smoke_snapshots.parquet'
```

- [ ] **Step 6: Explicitly route the K-avg CSV to `OUT` (not derived from `outfile`)**

Find (around line 394):
```python
        scalars_csv = outfile.with_suffix('.kavg.csv')
```
Change to:
```python
        # kavg is small enough to commit; route to OUT (results/) not RAW_OUT.
        scalars_csv = OUT / f'{outfile.stem}.kavg.csv'
```

The `outfile.stem` gives `scenarios` for a full run and `scenarios_smoke` for smoke, matching the previous `.with_suffix` behaviour but explicitly landing in `OUT`.

- [ ] **Step 7: Verify all path routing by inspecting the resulting file**

Run:
```bash
grep -nE 'OUT |RAW_OUT|outfile\s*=|ts_parquet\s*=|snap_parquet\s*=|scalars_csv\s*=' run_scenarios.py
```

Expected output should show:
- Line ~58: both `OUT = ...` and `RAW_OUT = ...`
- Line ~312–313: both mkdir calls
- Lines ~317–319: outfile/ts/snap → `RAW_OUT`
- Lines ~336–338: smoke outfile/ts/snap → `RAW_OUT`
- Line ~394–395: scalars_csv → `OUT`

Confirm no `OUT / 'scenarios*.parquet'` or `OUT / 'scenarios*.jsonl'` lines remain (only the K-avg CSV goes to `OUT`).

- [ ] **Step 8: Verify the K-avg CSV path resolves correctly for both modes**

Run this one-liner to sanity-check `outfile.stem` semantics:
```bash
conda run -n starsim python -c "from pathlib import Path; p = Path('/x/scenarios.jsonl'); print(p.stem); q = Path('/x/scenarios_smoke.jsonl'); print(q.stem)"
```

Expected:
```
scenarios
scenarios_smoke
```

That confirms the K-avg CSV names will be `scenarios.kavg.csv` and `scenarios_smoke.kavg.csv` respectively.

- [ ] **Step 9: Commit**

```bash
git add run_scenarios.py
git commit -m "run_scenarios: route fat outputs to raw_results/, keep kavg in results/

jsonl, full timeseries.parquet, and full snapshots.parquet now land in
the gitignored raw_results/ dir. The K-avg CSV stays in results/ so it
remains committable. Smoke variants routed the same way."
```

---

### Task 4: Create `build_plot_data.py`

**Files:**
- Create: `build_plot_data.py` (repo root)

**Interfaces:**
- Consumes: `raw_results/scenarios_timeseries.parquet`, `raw_results/scenarios_snapshots.parquet` (from `run_scenarios.py` in Task 3, or from prior VM runs migrated in Task 2).
- Produces: `results/scenarios_timeseries.parquet`, `results/scenarios_snapshots.parquet` — slim slices at the same paths that `plotting/plot_slide6.py:30` and `exploratory/plot_epi.py:25-26` already read from.

- [ ] **Step 1: Create the script with filter constants + main logic + self-verification**

Create `build_plot_data.py` with this content:

```python
"""Build the committable slim `results/*.parquet` slices from the full
`raw_results/*.parquet` fat outputs of run_scenarios.py.

Filters are the union of what the 8 committed slide plots + fig_epi_overview
actually pull. Any slide adding a new arm or metric requires updating the
constants below.

Consumers of the slim files (do not edit paths — they align with these):
  - plotting/plot_slide{6,9,10,11}.py  reads results/scenarios_timeseries.parquet
  - exploratory/plot_epi.py            reads results/scenarios_timeseries.parquet
                                        + results/scenarios_snapshots.parquet

Design doc: docs/superpowers/specs/2026-07-20-plot-data-extract-design.md
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).parent
RAW = REPO / 'raw_results'
OUT = REPO / 'results'

# Cells needed by slides 6/9/10/11 + fig_epi_overview (SOC-only).
# Comments cite the specific plot script that pulls each cell.
PLOT_CELLS = {
    'SOC',                                          # all
    'POC_c-baseline_p-baseline_b-none',             # slide 6, 9
    'POC_c-baseline_p-low_b-none',                  # slide 9
    'POC_c-baseline_p-moderate_b-none',             # slide 9, 10
    'POC_c-baseline_p-high_b-none',                 # slide 9
    'POC_c-baseline_p-moderate_b-low',              # slide 10
    'POC_c-baseline_p-moderate_b-moderate',         # slide 10, 11
    'POC_c-baseline_p-moderate_b-high',             # slide 10
    'POC_c-low_p-moderate_b-moderate',              # slide 11
    'POC_c-moderate_p-moderate_b-moderate',         # slide 11
    'POC_c-high_p-moderate_b-moderate',             # slide 11
}
PLOT_RESULTS = {
    'prevalence',       # slide 6/9/10/11 row 0
    'new_infections',   # slide 6/9/10/11 row 1
    'prevalence_f',     # fig_epi_overview
    'prevalence_m',     # fig_epi_overview
}
PLOT_DISEASES = {'ng', 'ct', 'tv', 'syph', 'hiv'}
SNAP_YEAR = 2027  # fig_epi_overview cross-section year


def slim_timeseries():
    src = RAW / 'scenarios_timeseries.parquet'
    dst = OUT / 'scenarios_timeseries.parquet'
    if not src.exists():
        raise SystemExit(
            f'[build_plot_data] missing {src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    ts = pd.read_parquet(src)
    slim = ts[
        ts.cell.isin(PLOT_CELLS)
        & ts.result_name.isin(PLOT_RESULTS)
        & ts.disease.isin(PLOT_DISEASES)
    ].reset_index(drop=True)
    # Self-verify: every whitelisted cell that appears in raw must appear in slim.
    raw_cells = set(ts.cell.unique()) & PLOT_CELLS
    slim_cells = set(slim.cell.unique())
    missing = raw_cells - slim_cells
    assert not missing, f'lost cells during filter: {missing}'
    assert set(slim.cell.unique()) <= PLOT_CELLS, 'extra cells leaked through'
    assert set(slim.result_name.unique()) <= PLOT_RESULTS, 'extra result_names leaked'
    slim.to_parquet(dst, index=False, compression='zstd')
    print(f'timeseries: {len(ts):>7d} rows ({src.stat().st_size/1024:>6.0f} KB) '
          f'-> {len(slim):>7d} rows ({dst.stat().st_size/1024:>6.0f} KB)')


def slim_snapshots():
    src = RAW / 'scenarios_snapshots.parquet'
    dst = OUT / 'scenarios_snapshots.parquet'
    if not src.exists():
        raise SystemExit(
            f'[build_plot_data] missing {src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    sn = pd.read_parquet(src)
    slim = sn[(sn.cell == 'SOC') & (sn.year == SNAP_YEAR)].reset_index(drop=True)
    assert (slim.cell == 'SOC').all(), 'non-SOC cells leaked'
    assert (slim.year == SNAP_YEAR).all(), 'non-SNAP_YEAR rows leaked'
    slim.to_parquet(dst, index=False, compression='zstd')
    print(f'snapshots:  {len(sn):>7d} rows ({src.stat().st_size/1024:>6.0f} KB) '
          f'-> {len(slim):>7d} rows ({dst.stat().st_size/1024:>6.0f} KB)')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    slim_timeseries()
    slim_snapshots()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify the script parses**

Run:
```bash
conda run -n starsim python -c "import ast; ast.parse(open('build_plot_data.py').read()); print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Verify the missing-input error is helpful**

Temporarily hide the raw file and run the script to confirm the error path:
```bash
mv raw_results/scenarios_timeseries.parquet raw_results/scenarios_timeseries.parquet.hidden
conda run -n starsim python build_plot_data.py 2>&1 | head -5
mv raw_results/scenarios_timeseries.parquet.hidden raw_results/scenarios_timeseries.parquet
```

Expected: SystemExit with a message pointing at the missing file. No traceback, just the actionable text.

- [ ] **Step 4: Commit**

```bash
git add build_plot_data.py
git commit -m "build_plot_data: extract committable slim plot slices from raw_results/

Filter constants at the top define the exact (cell x result_name x disease)
slice needed by the 8 committed slide plots + fig_epi_overview. Runs
self-checks after each filter and writes zstd-compressed parquets."
```

---

### Task 5: Regenerate slim `results/*.parquet` from real data and commit

**Files:**
- Produce: `results/scenarios_timeseries.parquet` (slim)
- Produce: `results/scenarios_snapshots.parquet` (slim)

**Interfaces:**
- Consumes: `build_plot_data.py` from Task 4; `raw_results/*.parquet` migrated in Task 2.
- Produces: committed slim parquets that Task 8's plot regeneration will read.

- [ ] **Step 1: Run the extractor**

Run:
```bash
conda run -n starsim python build_plot_data.py
```

Expected: two lines like
```
timeseries:   94640 rows (   228 KB) ->   XXXX rows (   YYY KB)
snapshots:    33280 rows (   176 KB) ->    XXX rows (    YY KB)
```

The right-hand-side rows should be a small fraction of the left. TS output should have `len(PLOT_CELLS) * len(PLOT_RESULTS) * len(PLOT_DISEASES)` × years × draws ≈ 11 × 4 × 5 × ~55 × 5 ≈ 60k max (usually far less because not every combination exists). SNAP output should be roughly `n_ages × n_sexes × n_disease_bases` for a single cell and single year — expect a few hundred rows.

(Note: N_DRAWS=1 was used for the last run so counts will be ~5x smaller than the N_DRAWS=5 case; this doesn't affect correctness.)

- [ ] **Step 2: Verify the slim files have the expected cells**

Run:
```bash
conda run -n starsim python -c "
import pandas as pd
ts = pd.read_parquet('results/scenarios_timeseries.parquet')
sn = pd.read_parquet('results/scenarios_snapshots.parquet')
print('ts cells:', sorted(ts.cell.unique()))
print('ts result_names:', sorted(ts.result_name.unique()))
print('ts diseases:', sorted(ts.disease.unique()))
print('snap cells:', sorted(sn.cell.unique()))
print('snap years:', sorted(sn.year.unique()))
"
```

Expected:
- ts cells: the 11 in `PLOT_CELLS` (order-independent)
- ts result_names: `['new_infections', 'prevalence', 'prevalence_f', 'prevalence_m']`
- ts diseases: `['ct', 'hiv', 'ng', 'syph', 'tv']`
- snap cells: `['SOC']`
- snap years: `[2027]`

- [ ] **Step 3: Confirm file sizes are commit-friendly**

Run:
```bash
ls -la results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet
du -h results/scenarios*.parquet
```

Expected: total under 1 MB for the current N_DRAWS=1 run; will scale to ~500 KB + 30 KB at N_DRAWS=5. If TS is over 2 MB, stop and investigate — probably a filter didn't kick in.

- [ ] **Step 4: Commit the slim parquets**

```bash
git add results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet
git commit -m "results: commit slim plot-only parquet slices

Filtered to the 11 cells and 4 result_names actually used by the 8 slide
plots + fig_epi_overview. Regenerable via build_plot_data.py."
```

---

### Task 6: Update exploratory scripts to read fat parquets from `raw_results/`

**Files:**
- Modify: `exploratory/plot_layering.py:21` (TS constant)
- Modify: `exploratory/plot_layering_newinf.py:19` (TS constant)
- Modify: `exploratory/plot_validation.py:25` (smoke TS constant only; smoke KAVG stays)

Do NOT touch:
- `exploratory/plot_epi.py` — reads `results/scenarios_timeseries.parquet` (SOC is in the slim file) and `results/scenarios_snapshots.parquet` (SOC + 2027 is exactly what the slim file has). Works unchanged against the slim files.
- `exploratory/plot_validation_pn.py`, `exploratory/plot_validation_yield.py` — read only the small K-avg CSV in `results/`, no change needed.

**Interfaces:**
- Consumes: `raw_results/scenarios_timeseries.parquet` and `raw_results/scenarios_smoke_timeseries.parquet` from Task 3's `run_scenarios.py` output.
- Produces: exploratory scripts that continue to work on the VM where `raw_results/` has the full parquets.

- [ ] **Step 1: Update `plot_layering.py`**

Edit `exploratory/plot_layering.py` line 21:
```python
TS = REPO / 'results' / 'scenarios_timeseries.parquet'
```
Change to:
```python
TS = REPO / 'raw_results' / 'scenarios_timeseries.parquet'
```

- [ ] **Step 2: Update `plot_layering_newinf.py`**

Edit `exploratory/plot_layering_newinf.py` line 19 with the identical change.

- [ ] **Step 3: Update `plot_validation.py`**

Edit `exploratory/plot_validation.py` line 25:
```python
TS = REPO / 'results' / 'scenarios_smoke_timeseries.parquet'
```
Change to:
```python
TS = REPO / 'raw_results' / 'scenarios_smoke_timeseries.parquet'
```

Do NOT change line 26 (`KAVG = REPO / 'results' / 'scenarios_smoke.kavg.csv'`) — smoke kavg stays in `results/`.

- [ ] **Step 4: Verify all three edits landed and no other exploratory script was missed**

Run:
```bash
grep -n "results.*scenarios.*parquet\|raw_results.*scenarios.*parquet" exploratory/plot_*.py
```

Expected: exactly three lines pointing at `raw_results/` (the three edits above), and one line in `plot_epi.py` pointing at `results/scenarios_timeseries.parquet`, and one line in `plot_epi.py` pointing at `results/scenarios_snapshots.parquet`. No stray `results/scenarios_timeseries.parquet` or `results/scenarios_smoke_timeseries.parquet` references outside plot_epi.py.

- [ ] **Step 5: Verify each edited script still imports cleanly**

Run:
```bash
conda run -n starsim python -c "
import ast
for p in ['exploratory/plot_layering.py', 'exploratory/plot_layering_newinf.py', 'exploratory/plot_validation.py']:
    ast.parse(open(p).read())
    print('ok', p)
"
```

Expected: three `ok` lines.

- [ ] **Step 6: Commit**

```bash
git add exploratory/plot_layering.py exploratory/plot_layering_newinf.py exploratory/plot_validation.py
git commit -m "exploratory: point layering + validation-TS scripts at raw_results/

The slim results/*.parquet files no longer contain the cells/metrics these
scripts need. They continue to work on the VM where raw_results/ has the
full outputs."
```

---

### Task 7: Update CLAUDE.md's VM-only data files section

**Files:**
- Modify: `CLAUDE.md` — the "VM-only data files (note for the local agent)" section.

**Interfaces:**
- Consumes: nothing.
- Produces: accurate CLAUDE.md so the next agent session understands the new `results/` vs `raw_results/` split.

- [ ] **Step 1: Read the current section to see exactly what to replace**

Run: `grep -n "VM-only data files" CLAUDE.md`

Then read from that line for 20 lines to see the whole section.

- [ ] **Step 2: Replace the section**

Edit `CLAUDE.md`. The current section starts at the line matching `## VM-only data files (note for the local agent)` and continues through the bullet list about `scenarios.jsonl`, `scenarios_timeseries.parquet`, etc., ending before `## Intake` or the next `##` header.

Replace that whole section with:

```markdown
## Results layout: `results/` (committable) vs `raw_results/` (VM-only)

`results/` is 100% committable — safe on any clone. `raw_results/` is
gitignored; it holds the fat outputs of a full factorial run and only
exists on the IDM Azure VM (or wherever `run_scenarios.py` last ran).

**In `results/` (committed):**
- `scenarios.kavg.csv` — K=5-averaged scalar table (65 cells × N_DRAWS rows).
- `scenarios_timeseries.parquet` — **slim** slice for the deck: 11 cells (SOC
  + the 10 POC arms across slides 6/9/10/11) × 4 result_names
  (`prevalence`, `new_infections`, `prevalence_f`, `prevalence_m`) × 5
  diseases. Source for `plotting/plot_slide{6,9,10,11}.py` and
  `exploratory/plot_epi.py`.
- `scenarios_snapshots.parquet` — **slim** slice: SOC only, year 2027 only.
  Source for `figures/supplementary/fig_epi_overview.png` via `exploratory/plot_epi.py`.
- `specificity.csv`, `soc_overtreatment.csv`, `ppv_table.csv`,
  `ng_confusion.csv`, `pn_story.json`, `pn_partner_counts.csv`,
  `vds_etiology.csv` — small diagnostics outputs from `diagnostics/*.py`.

**In `raw_results/` (gitignored, VM-only):**
- `scenarios.jsonl` — per-sim raw scalars.
- `scenarios_timeseries.parquet` — full 65-cell × N_DRAWS K-averaged TS.
- `scenarios_snapshots.parquet` — full 65-cell × N_DRAWS × 4-year age×sex snapshots.
- `scenarios_smoke.*` — smoke variants of the above.

**Regenerating the slim `results/*.parquet`:** after `python run_scenarios.py`
writes to `raw_results/`, run `python build_plot_data.py` to refresh the
committable slim files.

**Exploratory scripts** (`exploratory/plot_layering*.py`,
`exploratory/plot_validation.py`) read from `raw_results/` directly and only
run on the VM. `exploratory/plot_epi.py` reads the slim `results/` files and
works on any clone.
```

- [ ] **Step 3: Verify no stale references remain to results/scenarios.jsonl etc.**

Run:
```bash
grep -nE 'results/scenarios.jsonl|results/scenarios_timeseries.parquet.*NOT committed|results/scenarios_snapshots.parquet.*NOT committed' CLAUDE.md
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "CLAUDE.md: document results/ vs raw_results/ split"
```

---

### Task 8: End-to-end verification — regenerate every in-scope figure against slim `results/`

**Files:**
- Verifies (does not modify): `figures/fig_slide{3,5,6,9,10,11,12,13}.png` and `figures/supplementary/fig_epi_overview.png`. Any PNG diff is a review point, not automatic acceptance.

**Interfaces:**
- Consumes: everything from tasks 1–7.
- Produces: confirmation that the slim `results/` is sufficient for every in-scope plot. No new commits unless a figure legitimately changed.

- [ ] **Step 1: Regenerate the 8 slide plots**

Run:
```bash
cd plotting
for f in plot_slide3.py plot_slide5.py plot_slide6.py plot_slide9.py plot_slide10.py plot_slide11.py plot_slide12.py plot_slide13.py; do
  echo "=== $f ==="
  conda run -n starsim python "$f" 2>&1 | tail -3
done
cd ..
```

Expected: each script prints `wrote figures/fig_slideNN.png` (or similar) and exits 0. No `KeyError`, no `IndexError`, no traceback.

- [ ] **Step 2: Regenerate the supplementary fig_epi_overview**

Run:
```bash
conda run -n starsim python exploratory/plot_epi.py 2>&1 | tail -5
```

Expected: prints `wrote figures/supplementary/fig_epi_overview.png`, exits 0.

- [ ] **Step 3: Confirm all 9 figures exist and are non-empty**

Run:
```bash
ls -la figures/fig_slide{3,5,6,9,10,11,12,13}.png figures/supplementary/fig_epi_overview.png
```

Expected: all 9 files present with non-zero sizes.

- [ ] **Step 4: Review PNG diffs (if any)**

Run: `git status figures/`

If any of the 9 PNGs show as modified, open them and eyeball vs. the committed version. Numeric outputs are identical (we only filtered rows, didn't downcast), but matplotlib rasterisation can drift slightly across environments. Diffs should be visually indistinguishable. If they are, commit the regenerated PNGs; if not, investigate.

- [ ] **Step 5: (If figures changed) commit**

```bash
git add figures/fig_slide*.png figures/supplementary/fig_epi_overview.png
git commit -m "figures: regenerate against slim results/ (visual identity check)"
```

Skip this step if `git status figures/` is clean.

- [ ] **Step 6: Final smoke — try a fresh clone workflow**

Simulate what a Mac clone would experience:
```bash
# In a scratch dir, verify plots run without raw_results/ present:
cd /tmp && rm -rf sti_clone_check && git clone /home/robyn/sti_notification sti_clone_check
cd sti_clone_check
conda run -n starsim python plotting/plot_slide6.py 2>&1 | tail -3
conda run -n starsim python exploratory/plot_epi.py 2>&1 | tail -3
cd /home/robyn/sti_notification && rm -rf /tmp/sti_clone_check
```

Expected: both scripts write PNGs successfully without `raw_results/` existing on disk. If either script complains about a missing file in `raw_results/`, that's a bug — a slide plot or fig_epi_overview is silently reading from the wrong path.

---

## Self-review

**1. Spec coverage.** Each spec section maps to a task:
- Directory layout → Tasks 1, 2, 3
- `build_plot_data.py` → Task 4
- `run_scenarios.py` edits → Task 3
- Migration → Task 2
- Exploratory-script path updates → Task 6
- CLAUDE.md update → Task 7
- Success criteria (results/ committable, plots work on fresh clone) → verified in Task 8

**2. Placeholder scan.** No TBDs; every code step contains full code; every command has expected output.

**3. Type consistency.** `RAW_OUT` / `OUT` constants used identically in `run_scenarios.py` and `build_plot_data.py`. Filter constant names (`PLOT_CELLS`, `PLOT_RESULTS`, `PLOT_DISEASES`, `SNAP_YEAR`) are defined once in `build_plot_data.py` and not referenced elsewhere. Path constants edited in exploratory scripts use identical string forms (`'raw_results'`) as `run_scenarios.py`.

One deviation from the writing-plans skill template: no separate pytest test files. This repo has no test infrastructure (`no tests/` dir, no `pytest.ini`) and the deliverable is a small pure-filter script; verification is done inline via assertions in `build_plot_data.py` and end-to-end regeneration in Task 8. Global Constraints call this out.
