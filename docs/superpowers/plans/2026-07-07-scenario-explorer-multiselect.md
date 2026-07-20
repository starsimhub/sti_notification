# Scenario Explorer Multi-Select + Time-Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Scenario Explorer's "pick one axis to vary, fix the other two, pick one disease" interaction with three independent multi-select checkbox groups (full cross-product across all three levers) and always-visible 2×2 disease subplots, adding time-series charts alongside the existing bar charts wherever the underlying data supports it.

**Architecture:** A new Python export step converts `results/scenarios_timeseries.parquet` (already present locally) into a small committed `timeseries.json` (median-per-year, no per-draw bands). Four new/rewritten `dataTransforms.js` functions replace the old vary-axis functions with cross-product equivalents. `MetricChart.jsx` gains a `'timeseries'` line-chart mode alongside its existing bar-chart modes (which need no changes). `ScenarioExplorer.jsx` is rewritten around the new checkbox-driven state model.

**Tech Stack:** Same as the existing dashboard — React 18, Vite 5, Tailwind CSS 3, Recharts 2, Vitest. Python/pandas (with `pyarrow`, confirmed installed in the `starsim` conda env) for the new parquet-reading export step.

## Global Constraints

- Diseases: `ng`, `ct`, `tv`, `syph` only — HIV stays excluded everywhere, as in the original dashboard build.
- Metrics: `prevalence`, `new_inf`, `overtreatment`, `notification` — no `undertreatment`, as established previously.
- Time series covers `prevalence` and `new_inf` only, years 2027–2040 only. `overtreatment` and `notification` have no annual data and stay bar-chart only.
- Syphilis's time-series prevalence must use the `sexually_transmissible_prevalence` parquet column, not the generic `prevalence` column, to stay consistent with the bar chart's existing syph-specific handling in `export_data.py`.
- Time-series lines show medians only — no IQR bands. Bars keep their existing IQR error bars, unchanged.
- Default checkbox state is `{ care: ['baseline'], pn: ['baseline'], bp: ['none'] }` (SOC's own levels) — exactly 1 POC combo + SOC = 2 series on first paint.
- Each checkbox group must always have at least one level checked (clicking the last checked box is a no-op).
- A non-blocking warning appears once the checked cross-product exceeds 8 combinations.
- `DiseaseSelect.jsx` and `LadderLevelSelect.jsx` become dead code and must be deleted, not left unused.
- `groupedSeries`/`notificationSeries` in `dataTransforms.js` are replaced, not kept alongside their cross-product equivalents; their tests are rewritten, not left testing deleted code.

---

## File Structure

```
dashboard/
├── scripts/export_data.py           # + export_timeseries()
├── src/
│   ├── data/
│   │   └── timeseries.json          # NEW — generated
│   ├── components/
│   │   ├── controls/
│   │   │   ├── DiseaseSelect.jsx        # DELETE
│   │   │   ├── LadderLevelSelect.jsx    # DELETE
│   │   │   └── LadderCheckboxGroup.jsx  # NEW
│   │   └── sections/
│   │       ├── MetricChart.jsx      # + 'timeseries' mode
│   │       └── ScenarioExplorer.jsx # rewritten
│   └── utils/
│       ├── dataTransforms.js        # groupedSeries/notificationSeries -> crossProduct* + timeSeriesForCombos
│       └── dataTransforms.test.js   # rewritten
```

## Exact data shapes locked in for this plan

**`src/data/timeseries.json`** — flat array, one record per (combo, disease, metric, year):
```json
{ "care_level": "baseline", "pn_level": "low", "bp_level": "none", "poc": true, "disease": "ng", "metric": "prevalence", "year": 2027, "value": 0.0812 }
```
`metric` is `"prevalence"` or `"new_inf"` (matching the bar-chart metric keys, not the parquet's raw `result_name`). `value` is the median across the 5 draws for that (combo, disease, metric, year) — computed in Python, never re-derived in JS.

**`crossProductCombos(selectedLevels) -> array<{care_level, pn_level, bp_level, label}>`** — cartesian product; `label` is `"${care} / ${pn} / ${bp}"`.

**`crossProductBarSeries(scenarios, {combos, disease, metric}) -> array<{label, isSoc, median, p25, p75}>`** — same shape `MetricChart`'s `'single'` mode already consumes; SOC prepended once, one entry per combo.

**`crossProductNotificationSeries(scenarios, {combos}) -> array<{label, isSoc, over: {median,p25,p75}, under: {median,p25,p75}}>`** — same shape `MetricChart`'s `'notification'` mode already consumes.

**`timeSeriesForCombos(timeseries, {combos, disease, metric}) -> array<{label, isSoc, points: [{year, value}]}>`** — consumed by `MetricChart`'s new `'timeseries'` mode.

---

## Task 1: `export_timeseries()` in `export_data.py`

**Files:**
- Modify: `dashboard/scripts/export_data.py`

**Interfaces:**
- Consumes: `results/scenarios_timeseries.parquet` (columns: `cell, care, pn, bp, poc, draw, disease, result_name, year, value`; confirmed present locally, 473,200 rows, 5 diseases × up to 10 `result_name` values × 56 years × 65 cells × 5 draws).
- Produces: `dashboard/src/data/timeseries.json` in the shape locked in above.

- [ ] **Step 1: Add the time-series export function to `dashboard/scripts/export_data.py`**

Add these constants near the top of the file, after the existing `DISEASES`/`PREV_COL` block:

```python
TS_DISEASES = ['ng', 'ct', 'tv', 'syph']
TS_RESULT_NAME = {d: 'prevalence' for d in TS_DISEASES}
TS_RESULT_NAME['syph'] = 'sexually_transmissible_prevalence'
TS_YEAR_START = 2027
TS_YEAR_END = 2040
```

Add this function after `export_scenarios()`:

```python
def export_timeseries():
    df = pd.read_parquet(REPO_ROOT / 'results' / 'scenarios_timeseries.parquet')
    df = df[(df['year'] >= TS_YEAR_START) & (df['year'] <= TS_YEAR_END)]

    records = []
    for d in TS_DISEASES:
        prev_rows = df[(df['disease'] == d) & (df['result_name'] == TS_RESULT_NAME[d])]
        inf_rows = df[(df['disease'] == d) & (df['result_name'] == 'new_infections')]
        for metric, rows in (('prevalence', prev_rows), ('new_inf', inf_rows)):
            grouped = rows.groupby(['care', 'pn', 'bp', 'poc', 'year'])['value'].median().reset_index()
            for _, row in grouped.iterrows():
                records.append({
                    'care_level': row['care'],
                    'pn_level': row['pn'],
                    'bp_level': row['bp'],
                    'poc': bool(row['poc']),
                    'disease': d,
                    'metric': metric,
                    'year': int(row['year']),
                    'value': row['value'],
                })
    dest = DATA_DIR / 'timeseries.json'
    dest.write_text(json.dumps(records, indent=2, allow_nan=False))
    print(f'Wrote {len(records)} records to {dest}')
```

- [ ] **Step 2: Call it from `__main__`**

In `dashboard/scripts/export_data.py`, change:

```python
if __name__ == '__main__':
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_scenarios()
    export_ladders()
    export_diagnostic_performance()
```

to:

```python
if __name__ == '__main__':
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_scenarios()
    export_ladders()
    export_diagnostic_performance()
    export_timeseries()
```

- [ ] **Step 3: Run the export**

Run: `conda run -n starsim python dashboard/scripts/export_data.py`
Expected: prints the existing three "Wrote ..." lines plus a new `Wrote 7280 records to .../timeseries.json` (65 cells × 4 diseases × 2 metrics × 14 years = 7280).

- [ ] **Step 4: Spot-check the output**

Run:
```bash
python3 -c "
import json
d = json.load(open('dashboard/src/data/timeseries.json'))
print(len(d))
print(sorted(set(r['metric'] for r in d)))
print(sorted(set(r['disease'] for r in d)))
print(sorted(set(r['year'] for r in d)))
soc = [r for r in d if r['poc'] is False and r['disease']=='ng' and r['metric']=='prevalence']
print(sorted(soc, key=lambda r: r['year'])[:3])
"
```
Expected: `7280`, `['new_inf', 'prevalence']`, `['ct', 'ng', 'syph', 'tv']`, years `2027` through `2040` (14 values), and the SOC NG-prevalence rows sorted by year with plausible (non-null, non-negative) values.

- [ ] **Step 5: Commit**

```bash
git add dashboard/scripts/export_data.py dashboard/src/data/timeseries.json
git commit -m "dashboard: add time-series export (prevalence + new_inf, 2027-2040)"
```

---

## Task 2: Cross-product data transforms, with rewritten tests

**Files:**
- Modify: `dashboard/src/utils/dataTransforms.js`
- Modify: `dashboard/src/utils/dataTransforms.test.js`

**Interfaces:**
- Consumes: `filterRows`, `medIqr`, `getMetricValue` (all unchanged, already in the file).
- Produces: `crossProductCombos`, `crossProductBarSeries`, `crossProductNotificationSeries`, `timeSeriesForCombos` — exact signatures as locked in above. `groupedSeries`/`notificationSeries` and the `AXIS_TO_FIELD` constant they used are removed.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `dashboard/src/utils/dataTransforms.test.js` with:

```js
import { describe, it, expect } from 'vitest';
import {
  quantile, medIqr, filterRows, getMetricValue,
  crossProductCombos, crossProductBarSeries, crossProductNotificationSeries, timeSeriesForCombos,
} from './dataTransforms.js';

describe('quantile', () => {
  it('returns the median for q=0.5 on an odd-length array', () => {
    expect(quantile([1, 2, 3, 4, 5], 0.5)).toBe(3);
  });
  it('interpolates between points for q not landing exactly on an index', () => {
    expect(quantile([1, 2, 3, 4], 0.25)).toBeCloseTo(1.75, 5);
  });
});

describe('medIqr', () => {
  it('computes median/p25/p75 over numeric values, ignoring nulls', () => {
    const result = medIqr([1, 2, 3, 4, 5, null, undefined]);
    expect(result.median).toBe(3);
    expect(result.p25).toBeCloseTo(2, 5);
    expect(result.p75).toBeCloseTo(4, 5);
  });
  it('returns nulls for an empty or all-null input', () => {
    expect(medIqr([null, null])).toEqual({ median: null, p25: null, p75: null });
  });
});

const MOCK_ROWS = [
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, draw: 1,
    diseases: { ng: { prev_end: 0.10, new_inf: 100, overtreatment_rate: 0.5 } },
    notification: { over_notification_rate: 0.5, under_notification_rate: 0.3 } },
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, draw: 2,
    diseases: { ng: { prev_end: 0.12, new_inf: 110, overtreatment_rate: 0.6 } },
    notification: { over_notification_rate: 0.6, under_notification_rate: 0.4 } },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.08, new_inf: 90, overtreatment_rate: 0.3 } },
    notification: { over_notification_rate: 0.3, under_notification_rate: 0.2 } },
  { care_level: 'baseline', pn_level: 'moderate', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.06, new_inf: 80, overtreatment_rate: 0.2 } },
    notification: { over_notification_rate: 0.2, under_notification_rate: 0.1 } },
];

describe('filterRows', () => {
  it('filters on the given keys only, leaving omitted keys unconstrained', () => {
    expect(filterRows(MOCK_ROWS, { poc: false }).length).toBe(2);
    expect(filterRows(MOCK_ROWS, { poc: true, pn_level: 'low' }).length).toBe(1);
  });
});

describe('getMetricValue', () => {
  it('reads the prevalence field for a disease', () => {
    expect(getMetricValue(MOCK_ROWS[0], { disease: 'ng', metric: 'prevalence' })).toBe(0.10);
  });
  it('reads the overtreatment rate for a disease', () => {
    expect(getMetricValue(MOCK_ROWS[0], { disease: 'ng', metric: 'overtreatment' })).toBe(0.5);
  });
});

describe('crossProductCombos', () => {
  it('returns the cartesian product of the three selected-level arrays', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['baseline', 'low'], bp: ['none'] });
    expect(combos).toHaveLength(2);
    expect(combos[0]).toMatchObject({ care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' });
    expect(combos[1]).toMatchObject({ care_level: 'baseline', pn_level: 'low', bp_level: 'none' });
  });
  it('gives each combo a distinct, stable label', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    expect(combos[0].label).toBe('baseline / low / none');
  });
});

describe('crossProductBarSeries', () => {
  it('prepends SOC, then one entry per combo', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low', 'moderate'], bp: ['none'] });
    const result = crossProductBarSeries(MOCK_ROWS, { combos, disease: 'ng', metric: 'prevalence' });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true, median: 0.11 });
    expect(result.find((r) => r.label === combos[0].label)).toMatchObject({ median: 0.08 });
    expect(result.find((r) => r.label === combos[1].label)).toMatchObject({ median: 0.06 });
  });
});

describe('crossProductNotificationSeries', () => {
  it('prepends SOC with over/under sub-series, then one entry per combo', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    const result = crossProductNotificationSeries(MOCK_ROWS, { combos });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true });
    expect(result[0].over.median).toBeCloseTo(0.55, 5);
    expect(result[1].under.median).toBe(0.2);
  });
});

const MOCK_TIMESERIES = [
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, disease: 'ng', metric: 'prevalence', year: 2027, value: 0.10 },
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, disease: 'ng', metric: 'prevalence', year: 2028, value: 0.11 },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, disease: 'ng', metric: 'prevalence', year: 2027, value: 0.08 },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, disease: 'ng', metric: 'prevalence', year: 2028, value: 0.06 },
];

describe('timeSeriesForCombos', () => {
  it('returns SOC plus one entry per combo, each with year-sorted points', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    const result = timeSeriesForCombos(MOCK_TIMESERIES, { combos, disease: 'ng', metric: 'prevalence' });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true });
    expect(result[0].points).toEqual([{ year: 2027, value: 0.10 }, { year: 2028, value: 0.11 }]);
    expect(result[1].points).toEqual([{ year: 2027, value: 0.08 }, { year: 2028, value: 0.06 }]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd dashboard && npx vitest run`
Expected: FAIL — `crossProductCombos`/`crossProductBarSeries`/`crossProductNotificationSeries`/`timeSeriesForCombos` are not exported from `dataTransforms.js` yet.

- [ ] **Step 3: Update `dashboard/src/utils/dataTransforms.js`**

Remove the `AXIS_TO_FIELD` constant and the `groupedSeries`/`notificationSeries` functions (everything from `const AXIS_TO_FIELD = ...` to the end of the file), and replace with:

```js
export function crossProductCombos(selectedLevels) {
  const combos = [];
  for (const care of selectedLevels.care) {
    for (const pn of selectedLevels.pn) {
      for (const bp of selectedLevels.bp) {
        combos.push({
          care_level: care,
          pn_level: pn,
          bp_level: bp,
          label: `${care} / ${pn} / ${bp}`,
        });
      }
    }
  }
  return combos;
}

export function crossProductBarSeries(scenarios, { combos, disease, metric }) {
  const socRows = filterRows(scenarios, { poc: false });
  const soc = medIqr(socRows.map((r) => getMetricValue(r, { disease, metric })));
  const entries = combos.map((combo) => {
    const rows = filterRows(scenarios, {
      poc: true,
      care_level: combo.care_level,
      pn_level: combo.pn_level,
      bp_level: combo.bp_level,
    });
    const stats = medIqr(rows.map((r) => getMetricValue(r, { disease, metric })));
    return { label: combo.label, isSoc: false, ...stats };
  });
  return [{ label: 'SOC', isSoc: true, ...soc }, ...entries];
}

export function crossProductNotificationSeries(scenarios, { combos }) {
  const socRows = filterRows(scenarios, { poc: false });
  const socOver = medIqr(socRows.map((r) => r.notification.over_notification_rate));
  const socUnder = medIqr(socRows.map((r) => r.notification.under_notification_rate));
  const entries = combos.map((combo) => {
    const rows = filterRows(scenarios, {
      poc: true,
      care_level: combo.care_level,
      pn_level: combo.pn_level,
      bp_level: combo.bp_level,
    });
    return {
      label: combo.label,
      isSoc: false,
      over: medIqr(rows.map((r) => r.notification.over_notification_rate)),
      under: medIqr(rows.map((r) => r.notification.under_notification_rate)),
    };
  });
  return [{ label: 'SOC', isSoc: true, over: socOver, under: socUnder }, ...entries];
}

export function timeSeriesForCombos(timeseries, { combos, disease, metric }) {
  const byYear = (a, b) => a.year - b.year;
  const socPoints = timeseries
    .filter((r) => r.poc === false && r.disease === disease && r.metric === metric)
    .sort(byYear)
    .map((r) => ({ year: r.year, value: r.value }));
  const entries = combos.map((combo) => {
    const points = timeseries
      .filter((r) =>
        r.poc === true &&
        r.disease === disease &&
        r.metric === metric &&
        r.care_level === combo.care_level &&
        r.pn_level === combo.pn_level &&
        r.bp_level === combo.bp_level
      )
      .sort(byYear)
      .map((r) => ({ year: r.year, value: r.value }));
    return { label: combo.label, isSoc: false, points };
  });
  return [{ label: 'SOC', isSoc: true, points: socPoints }, ...entries];
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd dashboard && npx vitest run`
Expected: PASS, all tests green (9 existing behaviors preserved + 6 new test cases for the 4 new functions).

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/utils/dataTransforms.js dashboard/src/utils/dataTransforms.test.js
git commit -m "dashboard: replace vary-axis data transforms with cross-product + time-series equivalents"
```

---

## Task 3: `LadderCheckboxGroup.jsx`, delete `DiseaseSelect.jsx`/`LadderLevelSelect.jsx`

**Files:**
- Create: `dashboard/src/components/controls/LadderCheckboxGroup.jsx`
- Delete: `dashboard/src/components/controls/DiseaseSelect.jsx`
- Delete: `dashboard/src/components/controls/LadderLevelSelect.jsx`

**Interfaces:**
- Produces: `LadderCheckboxGroup({ label, levels, selected, onChange })` — `selected` is an array of currently-checked level strings; `onChange` receives the new full array. Enforces "at least one level stays checked" internally.

- [ ] **Step 1: Create `dashboard/src/components/controls/LadderCheckboxGroup.jsx`**

```jsx
export default function LadderCheckboxGroup({ label, levels, selected, onChange }) {
  function toggle(level) {
    if (selected.includes(level)) {
      if (selected.length === 1) return;
      onChange(selected.filter((l) => l !== level));
    } else {
      onChange([...selected, level]);
    }
  }
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <span className="text-sm font-medium text-brand-gray mr-1">{label}:</span>
      {levels.map((level) => (
        <label
          key={level}
          className="flex items-center gap-1.5 text-sm text-brand-gray capitalize cursor-pointer"
        >
          <input
            type="checkbox"
            checked={selected.includes(level)}
            onChange={() => toggle(level)}
            className="accent-brand-blue"
          />
          {level}
        </label>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Delete the two superseded control files**

```bash
git rm dashboard/src/components/controls/DiseaseSelect.jsx dashboard/src/components/controls/LadderLevelSelect.jsx
```

Note: `ScenarioExplorer.jsx` still imports both of these until Task 5 rewrites it — the app will not build cleanly again until Task 5 is done. This is expected; Task 4 (which doesn't touch `ScenarioExplorer.jsx`) will also not build in isolation for the same reason. Skip the build-verification step for this task and Task 4; the plan verifies the build once everything is wired up together in Task 5.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/controls/LadderCheckboxGroup.jsx
git commit -m "dashboard: add LadderCheckboxGroup, remove superseded DiseaseSelect/LadderLevelSelect"
```

---

## Task 4: `MetricChart.jsx` — add `'timeseries'` mode

**Files:**
- Modify: `dashboard/src/components/sections/MetricChart.jsx`

**Interfaces:**
- Consumes: the `{label, isSoc, points: [{year, value}]}` shape from `timeSeriesForCombos` (Task 2).
- Produces: `MetricChart({ data, mode: 'timeseries', yLabel })` in addition to the existing `'single'` and `'notification'` modes (both unchanged).

- [ ] **Step 1: Add the `Line`/`LineChart` imports and a color palette**

At the top of `dashboard/src/components/sections/MetricChart.jsx`, change:

```jsx
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts';

const SOC_COLOR = '#555555';
const SOC_UNDER_COLOR = '#999999';
const SERIES_COLORS = { median: '#0E7490', over: '#B35806', under: '#2E86C1' };
```

to:

```jsx
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const SOC_COLOR = '#555555';
const SOC_UNDER_COLOR = '#999999';
const SERIES_COLORS = { median: '#0E7490', over: '#B35806', under: '#2E86C1' };
const PALETTE = [
  '#0E7490', '#B35806', '#2E86C1', '#6A9F58', '#A6449B',
  '#C2871C', '#D6604D', '#4F6D7A', '#8C6D31', '#7570B3',
];

function paletteColor(index) {
  return PALETTE[index % PALETTE.length];
}
```

- [ ] **Step 2: Add the `'timeseries'` branch**

In `dashboard/src/components/sections/MetricChart.jsx`, immediately after the closing `}` of the `if (mode === 'single') { ... }` block (i.e. right before the notification-mode code that currently runs unconditionally), insert:

```jsx
  if (mode === 'timeseries') {
    const years = Array.from(
      new Set(data.flatMap((row) => row.points.map((p) => p.year)))
    ).sort((a, b) => a - b);
    const chartData = years.map((year) => {
      const point = { year };
      data.forEach((row, i) => {
        const found = row.points.find((p) => p.year === year);
        point[`series_${i}`] = found ? found.value : null;
      });
      return point;
    });
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" tick={{ fontSize: 12 }} />
          <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
          <Legend />
          {data.map((row, i) => (
            <Line
              key={row.label}
              type="monotone"
              dataKey={`series_${i}`}
              name={row.label}
              stroke={row.isSoc ? SOC_COLOR : paletteColor(i)}
              strokeWidth={row.isSoc ? 2.5 : 1.75}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/MetricChart.jsx
git commit -m "dashboard: add timeseries line-chart mode to MetricChart"
```

(Build verification is deferred to Task 5 — see the note in Task 3, Step 2.)

---

## Task 5: Rewrite `ScenarioExplorer.jsx`

**Files:**
- Modify: `dashboard/src/components/sections/ScenarioExplorer.jsx`

**Interfaces:**
- Consumes: `crossProductCombos`, `crossProductBarSeries`, `crossProductNotificationSeries`, `timeSeriesForCombos` (Task 2), `LadderCheckboxGroup` (Task 3), `MetricChart` in all three modes (Task 4 + existing), `MetricTabs` (unchanged, existing), `dashboard/src/data/timeseries.json` (Task 1).

- [ ] **Step 1: Replace the entire contents of `dashboard/src/components/sections/ScenarioExplorer.jsx`**

```jsx
import { useState, useMemo } from 'react';
import scenarios from '../../data/scenarios.json';
import timeseries from '../../data/timeseries.json';
import ladders from '../../data/ladders.json';
import {
  crossProductCombos, crossProductBarSeries, crossProductNotificationSeries, timeSeriesForCombos,
} from '../../utils/dataTransforms.js';
import MetricTabs from '../controls/MetricTabs.jsx';
import LadderCheckboxGroup from '../controls/LadderCheckboxGroup.jsx';
import MetricChart from './MetricChart.jsx';

const DISEASES = [
  { key: 'ng', label: 'Gonorrhoea' },
  { key: 'ct', label: 'Chlamydia' },
  { key: 'tv', label: 'Trichomoniasis' },
  { key: 'syph', label: 'Syphilis' },
];
const AXIS_LABELS = { care: 'Care-seeking', pn: 'PN intensity', bp: 'Bundled prevention' };
const DEFAULT_LEVELS = { care: ['baseline'], pn: ['baseline'], bp: ['none'] };
const COMBO_WARNING_THRESHOLD = 8;
const HAS_TIMESERIES = { prevalence: true, new_inf: true, overtreatment: false, notification: false };

const Y_LABELS = {
  prevalence: 'End-of-horizon prevalence',
  new_inf: 'New infections (cumulative)',
  overtreatment: 'Overtreatment rate',
  notification: 'Rate',
};

const TS_Y_LABELS = {
  prevalence: 'Prevalence',
  new_inf: 'New infections',
};

export default function ScenarioExplorer() {
  const [metric, setMetric] = useState('prevalence');
  const [selectedLevels, setSelectedLevels] = useState(DEFAULT_LEVELS);

  const combos = useMemo(() => crossProductCombos(selectedLevels), [selectedLevels]);

  const barDataByDisease = useMemo(() => {
    if (metric === 'notification') return null;
    const result = {};
    for (const { key } of DISEASES) {
      result[key] = crossProductBarSeries(scenarios, { combos, disease: key, metric });
    }
    return result;
  }, [combos, metric]);

  const notificationData = useMemo(() => {
    if (metric !== 'notification') return null;
    return crossProductNotificationSeries(scenarios, { combos });
  }, [combos, metric]);

  const tsDataByDisease = useMemo(() => {
    if (!HAS_TIMESERIES[metric]) return null;
    const result = {};
    for (const { key } of DISEASES) {
      result[key] = timeSeriesForCombos(timeseries, { combos, disease: key, metric });
    }
    return result;
  }, [combos, metric]);

  return (
    <section id="explorer" className="py-16 bg-brand-grayLight">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-2">Scenario explorer</h2>
        <p className="text-brand-gray mb-6 max-w-2xl">
          Check any combination of care-seeking, partner-notification, and bundled-prevention
          intensity levels to compare them side by side, across all four diseases. SOC (no POC,
          no added levers) is always shown as the gray reference.
        </p>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6 space-y-3">
          <MetricTabs value={metric} onChange={setMetric} />
          <LadderCheckboxGroup
            label={AXIS_LABELS.care}
            levels={ladders.care.levels}
            selected={selectedLevels.care}
            onChange={(levels) => setSelectedLevels((prev) => ({ ...prev, care: levels }))}
          />
          <LadderCheckboxGroup
            label={AXIS_LABELS.pn}
            levels={ladders.pn.levels}
            selected={selectedLevels.pn}
            onChange={(levels) => setSelectedLevels((prev) => ({ ...prev, pn: levels }))}
          />
          <LadderCheckboxGroup
            label={AXIS_LABELS.bp}
            levels={ladders.bp.levels}
            selected={selectedLevels.bp}
            onChange={(levels) => setSelectedLevels((prev) => ({ ...prev, bp: levels }))}
          />
          {combos.length > COMBO_WARNING_THRESHOLD && (
            <p className="text-xs text-amber-600">
              {combos.length} combinations selected — the chart may be hard to read. Consider
              unchecking a few boxes.
            </p>
          )}
        </div>

        {metric === 'notification' ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <MetricChart data={notificationData} mode="notification" yLabel={Y_LABELS.notification} />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {DISEASES.map(({ key, label }) => (
              <div key={key} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="font-semibold text-brand-blue mb-3">{label}</h3>
                <MetricChart data={barDataByDisease[key]} mode="single" yLabel={Y_LABELS[metric]} />
                {HAS_TIMESERIES[metric] && (
                  <div className="mt-4">
                    <MetricChart data={tsDataByDisease[key]} mode="timeseries" yLabel={TS_Y_LABELS[metric]} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Run the test suite**

Run: `cd dashboard && npx vitest run`
Expected: PASS (unaffected by this JSX-only change — confirms Task 2's rewritten tests still hold).

- [ ] **Step 3: Run the production build**

Run: `cd dashboard && npm run build`
Expected: succeeds, no errors, no unresolved-import warnings (confirms `DiseaseSelect.jsx`/`LadderLevelSelect.jsx` deletion didn't leave a dangling import anywhere).

- [ ] **Step 4: Manual verification**

Since no headless browser exists in this environment (established during the original dashboard build), verify at the data level: write and run a short Node/JS script (or use the pattern from the original build's task reports) that, for each metric (`prevalence`, `new_inf`, `overtreatment`, `notification`), computes what `ScenarioExplorer` would compute for the default `DEFAULT_LEVELS` state (1 combo + SOC) and for a state with 2+ checked levels on one axis, using the real `scenarios.json`/`timeseries.json` and the real `dataTransforms.js` functions — confirm every result is non-empty, non-null where expected, and that `timeSeriesForCombos` returns 14 points per series for `prevalence`/`new_inf`. Report exactly what was checked.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/sections/ScenarioExplorer.jsx
git commit -m "dashboard: rewrite ScenarioExplorer around multi-select cross-product + disease subplots"
```

---

## Self-review notes

- **Spec coverage:** checkbox multi-select on all 3 axes (Task 3+5), full cross-product (Task 2's `crossProductCombos`), always-all-4-diseases subplots (Task 5's `DISEASES.map`), bar + time-series "where possible" (Task 1's `TS_DISEASES`/metric restriction + Task 4's new mode + Task 5's `HAS_TIMESERIES` gate), syph's `sexually_transmissible_prevalence` special-case (Task 1 Step 1), median-only time-series lines vs IQR-banded bars (Task 4's `Line` has no error bar; existing `Bar`/`ErrorBar` code is untouched), default state + at-least-one-checked guard (Task 3's `LadderCheckboxGroup`, Task 5's `DEFAULT_LEVELS`), soft warning above 8 combos (Task 5), dead-code removal of `DiseaseSelect`/`LadderLevelSelect` (Task 3). All spec sections have a corresponding task.
- **Type/name consistency:** `crossProductCombos`'s combo objects (`{care_level, pn_level, bp_level, label}`, Task 2) are consumed identically in `crossProductBarSeries`/`crossProductNotificationSeries` (Task 2) and in `ScenarioExplorer.jsx`'s combo-count check (Task 5) — same field names throughout. `timeSeriesForCombos`'s `points: [{year, value}]` shape (Task 2) matches exactly what `MetricChart`'s new `'timeseries'` mode destructures (Task 4: `row.points.map((p) => p.year)`, `row.points.find((p) => p.year === year)`).
- **Placeholder scan:** no TBD/TODO; every step has literal code or an exact command with expected output.
