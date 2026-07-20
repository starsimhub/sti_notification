# Scenario Explorer multi-select + time-series redesign

## Purpose

Redesign `dashboard/src/components/sections/ScenarioExplorer.jsx` (built in the
initial dashboard project, see
`docs/superpowers/specs/2026-07-07-scenario-dashboard-design.md`) so a reader
can compare multiple lever combinations at once instead of one "varying axis"
at a time, always sees all four diseases side by side, and sees both an
endpoint bar chart and a time-series trajectory wherever the underlying data
supports it.

## Scope change from the original explorer

**Before:** pick one axis to vary (care-seeking / PN / bundled prevention),
fix the other two at a single level each, pick one disease. One chart shows
SOC + the 4 levels of the varying axis.

**After:** three independent checkbox groups (one per axis), each showing
that axis's levels; check any subset on any/all of them. The chart(s) show
every combination of checked levels as a separate line/bar (full
cross-product across all three axes) — e.g. checking 2 care levels, 3 PN
levels, and 1 BP level shows 6 combinations. All four diseases (NG, CT, TV,
syphilis) always show as separate subplots — the disease selector is removed.

## Data pipeline

### New: time-series export

`export_data.py` gains `export_timeseries()`, reading
`results/scenarios_timeseries.parquet` (473,200 rows: `cell, care, pn, bp,
poc, draw, disease, result_name, year, value`) and writing
`dashboard/src/data/timeseries.json`:

- Diseases: `ng`, `ct`, `tv`, `syph` only (same exclusion as the rest of the
  dashboard — HIV is not a dashboard disease).
- Metrics: `result_name` limited to `new_infections` and prevalence — for
  `syph` specifically, prevalence uses `sexually_transmissible_prevalence`
  (not the generic `prevalence` column), matching the special-case already in
  `export_data.py`'s `PREV_COL` override so the syph numbers shown here are
  consistent with the syph numbers in the bar charts and `scenarios.kavg.csv`.
  For `ng`/`ct`/`tv`, use the generic `prevalence` column.
- Years: 2027–2040 only (the intervention period — before 2027 every lever
  combination is identical to SOC by construction, so there's nothing to
  compare in the run-in years).
- One row per `(cell, disease, metric, year)`, value = **median across the
  5 draws for that cell** (no IQR band — time-series lines show medians only,
  per the scope decision below). Roughly 65 cells × 4 diseases × 2 metrics ×
  14 years ≈ 7,280 rows, small enough to commit directly.

### Unchanged: endpoint bar data

`scenarios.json` (325 per-draw records, built in the original dashboard
project) is untouched. Bar charts keep their IQR error bars, computed
client-side from the per-draw rows exactly as they do today.

## Component changes

**Removed** (become dead code once this ships):
- `dashboard/src/components/controls/DiseaseSelect.jsx` — disease is no
  longer a user choice.
- `dashboard/src/components/controls/LadderLevelSelect.jsx` — single-select
  pills are superseded by checkboxes; nothing else in the app uses this
  component.

**New:**
- `dashboard/src/components/controls/LadderCheckboxGroup.jsx` — one instance
  per axis (`care`/`pn`/`bp`), renders that axis's levels (from
  `ladders.json`) as checkboxes. Props: `{ label, levels, selected, onChange
  }`. Enforces "at least one level stays checked" — clicking the only
  checked box is a no-op, mirroring the guard pattern already used in
  `vmb-dashboard`'s multi-toggle control.

**Modified:**
- `MetricChart.jsx`'s existing `'single'` (bar) mode is reused as-is — it
  already renders whatever array of `{label, isSoc, median, p25, p75}`
  entries it receives, so a cross-product of N combos "just works" without
  changing that code path. Colors stay SOC-gray vs. one POC-teal for every
  non-SOC bar (not one color per combo — each bar's x-axis label already
  names its exact combination, and a distinct-color-per-bar legend would be
  unreadable once combo counts grow).
- New `'timeseries'` mode in `MetricChart.jsx`: a line chart, one line per
  combo, x-axis = year. Colors cycle through a small fixed categorical
  palette by combo index; SOC is always the same gray used elsewhere. A
  legend lists each combo's label. No IQR shading (see below).
- `dataTransforms.js`: `groupedSeries`/`notificationSeries` (the old
  vary-axis model) are **replaced**, not kept alongside, by:
  - `crossProductCombos(selectedLevels) -> array<{care_level, pn_level,
    bp_level, label}>` — cartesian product of the three checked-level
    arrays.
  - `crossProductBarSeries(scenarios, {combos, disease, metric}) ->
    array<{label, isSoc, median, p25, p75}>` — SOC prepended once, then one
    entry per combo, reusing `filterRows`/`medIqr`/`getMetricValue`.
  - `crossProductNotificationSeries(scenarios, {combos}) ->
    array<{label, isSoc, over: {...}, under: {...}}>` — same idea for the
    notification metric.
  - `timeSeriesForCombos(timeseries, {combos, disease, metric}) ->
    array<{label, isSoc, points: [{year, value}]}>` — reads the new
    `timeseries.json`.
  - Existing tests for `groupedSeries`/`notificationSeries` in
    `dataTransforms.test.js` are rewritten against the new functions, not
    kept as dead tests for removed code.
- `ScenarioExplorer.jsx`: state becomes `metric` (unchanged) plus
  `selectedLevels: { care: string[], pn: string[], bp: string[] }`,
  defaulting to `{ care: ['baseline'], pn: ['baseline'], bp: ['none'] }` —
  SOC's own levels, so the default view is SOC + exactly one POC combo (2
  lines/bars), legible from first paint. A small inline warning appears once
  the checked combination count exceeds 8, without blocking further
  selection (soft warning only, per the approved scope decision).

## Layout per metric tab

- **Prevalence / New infections:** 2×2 grid of disease panels (NG, CT, TV,
  syph). Each panel stacks a bar chart above a time-series chart (both use
  the same combo set and coloring).
- **Overtreatment:** same 2×2 disease grid, bar chart only — no time-series
  data exists for this metric (it's not among `scenarios_timeseries.parquet`'s
  `result_name` values).
- **Notification:** unchanged structurally from today — one chart, no
  disease dimension (over/under-notification isn't disease-specific) — but
  now driven by `crossProductNotificationSeries` instead of the old
  vary-axis state.

## Uncertainty treatment

Bars keep IQR error bars (unchanged — this is cheap to read even with many
bars, since each bar's position and label are unambiguous). Time-series
lines drop IQR bands entirely: with potentially many overlapping combos,
shaded bands would very quickly become unreadable "fog," so time series show
median trajectories only. This is an explicit scope decision, not an
oversight — the loss of uncertainty information in the time-series view is a
deliberate readability trade-off from a chart type that already shows more
comparisons (bars remain the place to see uncertainty per combination).

## Out of scope

- No hard cap on the number of checked combinations — only a soft, non-blocking
  warning above 8. Trusting the user's judgment per the approved scope
  decision.
- No change to `Overview.jsx`, `KeyFindings.jsx`, or `Methods.jsx` — this
  redesign is scoped entirely to `ScenarioExplorer.jsx` and its direct
  dependencies (`MetricChart.jsx`, the ladder/disease controls,
  `dataTransforms.js`, `export_data.py`).
- No deployment changes — the existing GitHub Pages workflow rebuilds
  `dashboard/` on every push to `main` regardless of what changed inside it.
