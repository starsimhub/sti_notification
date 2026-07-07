# Scenario Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `dashboard/`, a static React app inside `sti_notification` that lets a manuscript reader interactively explore the full 65-cell scenario factorial (prevalence, new infections, overtreatment, PN over/under-notification), plus an Overview and live-computed KeyFindings section drawn from the same data.

**Architecture:** Vite + React, styled with Tailwind (matching `vmb-dashboard`'s stack, the closer analogue of the two sibling dashboards — `klebsim-dashboard` uses plain CSS instead). A Python script (`scripts/export_data.py`) converts `results/scenarios.kavg.csv`, `results/slide4_diagnostic_performance.csv`, and the ladder dicts in `scenarios.py` into small JSON files under `src/data/`, committed and imported directly by React components (no runtime fetch/loading state needed — the dataset is ~325 rows, small enough to bundle). All derived rates (overtreatment, undertreatment, over/under-notification) are computed once in Python at export time, not recomputed in JS.

**Tech Stack:** React 18, Vite 5, Tailwind CSS 3, Recharts 2, Vitest (for `dataTransforms.js` unit tests). Python 3.11 / pandas for the export script (matches the repo's existing `starsim` conda env — no new Python deps).

## Global Constraints

- Dashboard lives at `sti_notification/dashboard/` (subfolder, not a separate repo), per the approved spec at `docs/superpowers/specs/2026-07-07-scenario-dashboard-design.md`.
- No server-side code. `npm run build` must produce a static `dist/` with no console errors.
- `scripts/export_data.py` is run manually (`conda run -n starsim python dashboard/scripts/export_data.py`) — not wired into CI.
- Ladder level labels and values must be imported from `scenarios.py`, never hardcoded in JS or in the export script.
- Deployment (Vercel/GitHub Pages) is explicitly out of scope for this plan.
- Deviations from the spec's literal file list, and why:
  - Data lives at `src/data/*.json` (direct ES import), not `public/data/*.json` (fetch). Same content, same export script; simpler for a bundle this small, matches `vmb-dashboard`'s pattern exactly.
  - The four chart components (`PrevalenceChart`, `NewInfectionsChart`, `OvertreatmentChart`, `NotificationChart`) are implemented as one generic `MetricChart.jsx` driven by a metric config, to avoid four near-duplicate files (DRY).
  - `results/ppv_table.csv` and `results/specificity.csv`/`soc_overtreatment.csv` are **not** used — `results/slide4_diagnostic_performance.csv` already contains the exact SOC/POC sens/spec/PPV/NPV table Overview needs, and `scenarios.kavg.csv`'s own `_new_treated_unnecessary`/`_new_treated_success` columns give overtreatment/undertreatment consistently across the whole factorial (specificity.csv only covers one draw). Pulling in the other CSVs would add data sources the dashboard doesn't need.

---

## File Structure

```
dashboard/
├── scripts/
│   └── export_data.py
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── index.html
├── src/
│   ├── main.jsx
│   ├── index.css
│   ├── App.jsx
│   ├── data/
│   │   ├── scenarios.json              # 325 records, one per (cell, draw)
│   │   ├── ladders.json                # care/pn/bp level order + params, from scenarios.py
│   │   └── diagnostic_performance.json # from results/slide4_diagnostic_performance.csv
│   ├── utils/
│   │   ├── dataTransforms.js
│   │   └── dataTransforms.test.js
│   └── components/
│       ├── layout/
│       │   ├── Header.jsx
│       │   └── Footer.jsx
│       ├── controls/
│       │   ├── DiseaseSelect.jsx
│       │   ├── MetricTabs.jsx
│       │   └── LadderLevelSelect.jsx   # reused 3x: vary-axis picker + 2 fixed-level pickers
│       └── sections/
│           ├── Overview.jsx
│           ├── ScenarioExplorer.jsx
│           ├── MetricChart.jsx
│           ├── KeyFindings.jsx
│           └── Methods.jsx
```

## Exact data shapes (locked in now so every later task agrees on field names)

**`src/data/scenarios.json`** — array of 325 objects:
```json
{
  "care_level": "baseline", "pn_level": "moderate", "bp_level": "high", "poc": true, "draw": 75,
  "diseases": {
    "hiv":  { "prev_end": 0.113, "new_inf": 976140.0, "new_treated": 0.0, "new_treated_success": 0.0, "new_treated_unnecessary": 0.0, "overtreatment_rate": null, "undertreatment_rate": null },
    "ng":   { "prev_end": 0.0081, "new_inf": 6391542.0, "new_treated": 1885986.0, "new_treated_success": 1096374.0, "new_treated_unnecessary": 744024.0, "overtreatment_rate": 0.3946, "undertreatment_rate": 0.4187 },
    "ct":   { "...": "same keys" },
    "tv":   { "...": "same keys" },
    "syph": { "...": "same keys" }
  },
  "notification": { "new_notified": 4469538.0, "new_index_total": 1996128.0, "over_notification_rate": 0.2697, "under_notification_rate": 0.1234 }
}
```
`overtreatment_rate = new_treated_unnecessary / new_treated` (null if `new_treated == 0`).
`undertreatment_rate = 1 - new_treated_success / new_inf` (null if `new_inf == 0`).
`over_notification_rate = notified_no_sti / new_notified` (null if `new_notified == 0`).
`under_notification_rate = 1 - (new_notified - notified_no_sti) / (new_index_total - new_index_no_sti)` (null if that denominator is 0).

**`src/data/ladders.json`**:
```json
{
  "care": { "levels": ["baseline", "low", "moderate", "high"], "values": { "baseline": 1.0, "low": 1.25, "moderate": 1.5, "high": 1.8 } },
  "pn":   { "levels": ["baseline", "low", "moderate", "high"] },
  "bp":   { "levels": ["none", "low", "moderate", "high"], "values": { "none": 0.0, "low": 0.25, "moderate": 0.5, "high": 0.75 } }
}
```

**`src/data/diagnostic_performance.json`** — direct records from `slide4_diagnostic_performance.csv`:
```json
[{ "disease": "Gonorrhoea", "arm": "SOC", "prev": 0.109, "sens": 0.7, "spec": 0.5, "PPV": 0.146, "NPV": 0.932, "FDR": 0.854, "FOR": 0.068 }, ...]
```

---

## Task 1: Scaffold the Vite + React + Tailwind app

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.js`
- Create: `dashboard/tailwind.config.js`
- Create: `dashboard/postcss.config.js`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.jsx`
- Create: `dashboard/src/index.css`
- Create: `dashboard/src/App.jsx`
- Create: `dashboard/.gitignore`

**Interfaces:**
- Produces: a running `npm run dev` dev server and a passing `npm run build`, with an `App.jsx` that later tasks will extend by importing new section components.

- [ ] **Step 1: Create `dashboard/package.json`**

```json
{
  "name": "sti-notification-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "recharts": "^2.12.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "vite": "^5.4.1",
    "vitest": "^2.1.1"
  }
}
```

- [ ] **Step 2: Create `dashboard/vite.config.js`**

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  test: {
    environment: 'node',
  },
});
```

- [ ] **Step 3: Create `dashboard/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          teal: '#0E7490',
          blue: '#1B4F72',
          gray: '#6B7280',
          grayLight: '#F3F4F6',
          soc: '#555555',
        },
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 4: Create `dashboard/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 5: Create `dashboard/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>STI Notification — Scenario Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Create `dashboard/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: Create `dashboard/src/main.jsx`**

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 8: Create `dashboard/src/App.jsx`** (placeholder body — later tasks add sections)

```jsx
export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <main className="flex-1">
        <p className="p-8 text-brand-gray">Dashboard scaffold — sections added in later tasks.</p>
      </main>
    </div>
  );
}
```

- [ ] **Step 9: Create `dashboard/.gitignore`**

```
node_modules/
dist/
```

- [ ] **Step 10: Install and verify build**

Run: `cd dashboard && npm install && npm run build`
Expected: `dist/` created, no errors, ends with `✓ built in <time>`.

- [ ] **Step 11: Commit**

```bash
git add dashboard/package.json dashboard/vite.config.js dashboard/tailwind.config.js dashboard/postcss.config.js dashboard/index.html dashboard/src/main.jsx dashboard/src/index.css dashboard/src/App.jsx dashboard/.gitignore
git commit -m "dashboard: scaffold Vite + React + Tailwind app"
```

---

## Task 2: `export_data.py` — scenarios.json and ladders.json

**Files:**
- Create: `dashboard/scripts/export_data.py`
- Test: manual (run and inspect output; Python side has no existing test harness for one-off export scripts, matching `klebsim-dashboard/scripts/export_data.py`'s convention of no test file)

**Interfaces:**
- Consumes: `results/scenarios.kavg.csv` (325 rows, columns as described in the spec), `scenarios.py`'s `PN_INTENSITY`, `CARE_SEEKING`, `BUNDLED_PREVENTION`, `CARE_LEVELS`, `PN_LEVELS`, `BP_LEVELS`.
- Produces: `dashboard/src/data/scenarios.json`, `dashboard/src/data/ladders.json` with the exact shapes locked in above.

- [ ] **Step 1: Write `dashboard/scripts/export_data.py`**

```python
"""Export scenarios.kavg.csv + scenario ladder definitions to dashboard/src/data/."""

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]   # sti_notification/
DATA_DIR = Path(__file__).resolve().parents[1] / 'src' / 'data'

sys.path.insert(0, str(REPO_ROOT))
from scenarios import (          # noqa: E402
    CARE_SEEKING, PN_INTENSITY, BUNDLED_PREVENTION,
    CARE_LEVELS, PN_LEVELS, BP_LEVELS,
)

DISEASES = ['hiv', 'ng', 'ct', 'tv', 'syph']
PREV_COL = {d: f'{d}_prev_end' for d in DISEASES}
PREV_COL['syph'] = 'syph_sti_prev_end'


def safe_div(numer, denom):
    if denom == 0 or pd.isna(denom):
        return None
    return numer / denom


def export_scenarios():
    df = pd.read_csv(REPO_ROOT / 'results' / 'scenarios.kavg.csv')
    records = []
    for _, row in df.iterrows():
        diseases = {}
        for d in DISEASES:
            new_inf = row[f'{d}_new_inf']
            new_treated = row[f'{d}_new_treated']
            new_treated_success = row[f'{d}_new_treated_success']
            new_treated_unnecessary = row[f'{d}_new_treated_unnecessary']
            diseases[d] = {
                'prev_end': row[PREV_COL[d]],
                'new_inf': new_inf,
                'new_treated': new_treated,
                'new_treated_success': new_treated_success,
                'new_treated_unnecessary': new_treated_unnecessary,
                'overtreatment_rate': safe_div(new_treated_unnecessary, new_treated),
                'undertreatment_rate': (
                    None if pd.isna(safe_div(new_treated_success, new_inf))
                    or safe_div(new_treated_success, new_inf) is None
                    else 1 - safe_div(new_treated_success, new_inf)
                ),
            }
        new_notified = row['pn_new_notified']
        notified_no_sti = row['pn_new_notified_no_sti']
        index_total = row['pn_new_index_total']
        index_no_sti = row['pn_new_index_no_sti']
        notification = {
            'new_notified': new_notified,
            'new_index_total': index_total,
            'over_notification_rate': safe_div(notified_no_sti, new_notified),
            'under_notification_rate': (
                None if safe_div(new_notified - notified_no_sti, index_total - index_no_sti) is None
                else 1 - safe_div(new_notified - notified_no_sti, index_total - index_no_sti)
            ),
        }
        records.append({
            'care_level': row['care'],
            'pn_level': row['pn'],
            'bp_level': row['bp'],
            'poc': bool(row['poc']),
            'draw': int(row['draw']),
            'diseases': diseases,
            'notification': notification,
        })
    dest = DATA_DIR / 'scenarios.json'
    dest.write_text(json.dumps(records, indent=2, allow_nan=False))
    print(f'Wrote {len(records)} records to {dest}')


def export_ladders():
    ladders = {
        'care': {'levels': CARE_LEVELS, 'values': CARE_SEEKING},
        'pn': {'levels': PN_LEVELS},
        'bp': {'levels': BP_LEVELS, 'values': {k: v['coverage'] for k, v in BUNDLED_PREVENTION.items()}},
    }
    dest = DATA_DIR / 'ladders.json'
    dest.write_text(json.dumps(ladders, indent=2))
    print(f'Wrote ladders.json to {dest}')


def export_diagnostic_performance():
    df = pd.read_csv(REPO_ROOT / 'results' / 'slide4_diagnostic_performance.csv')
    dest = DATA_DIR / 'diagnostic_performance.json'
    dest.write_text(json.dumps(df.to_dict(orient='records'), indent=2))
    print(f'Wrote {len(df)} records to {dest}')


if __name__ == '__main__':
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_scenarios()
    export_ladders()
    export_diagnostic_performance()
```

- [ ] **Step 2: `new_treated_unnecessary` can exceed `new_treated` is impossible but `new_inf == 0` (HIV rows show this) must not crash — verify by running**

Run: `conda run -n starsim python dashboard/scripts/export_data.py`
Expected: prints `Wrote 325 records...`, `Wrote ladders.json...`, `Wrote 8 records...`, no traceback.

- [ ] **Step 3: Spot-check the output**

Run: `python3 -c "import json; d=json.load(open('dashboard/src/data/scenarios.json')); print(len(d)); print(d[0]['diseases']['hiv']); print(d[0]['diseases']['ng'])"`
Expected: `325`, then a dict showing `overtreatment_rate: None` and `undertreatment_rate: None` for `hiv` (since `hiv_new_treated`/`hiv_new_inf` are 0 in most rows — HIV testing/treatment isn't modeled as a PN-driven pathway the way NG/CT/TV/syph are), and non-null numeric rates for `ng`.

- [ ] **Step 4: Commit**

```bash
git add dashboard/scripts/export_data.py dashboard/src/data/scenarios.json dashboard/src/data/ladders.json dashboard/src/data/diagnostic_performance.json
git commit -m "dashboard: add export_data.py, generate scenarios/ladders/diagnostic-performance JSON"
```

---

## Task 3: `dataTransforms.js` with unit tests

**Files:**
- Create: `dashboard/src/utils/dataTransforms.js`
- Create: `dashboard/src/utils/dataTransforms.test.js`

**Interfaces:**
- Consumes: the `scenarios.json` record shape from Task 2 (`{care_level, pn_level, bp_level, poc, draw, diseases, notification}`).
- Produces (used by Task 4 controls and Task 5 explorer/chart):
  - `quantile(sortedArr, q) -> number`
  - `medIqr(values) -> {median, p25, p75}` (values: array of numbers, nulls filtered out; returns `{median: null, p25: null, p75: null}` if empty)
  - `filterRows(scenarios, {poc, care_level, pn_level, bp_level}) -> array` (any key omitted = no filter on that key)
  - `getMetricValue(row, {disease, metric}) -> number|null` where `metric` is one of `'prevalence' | 'new_inf' | 'overtreatment' | 'undertreatment'`
  - `groupedSeries(scenarios, {varyAxis, disease, metric, fixed}) -> array<{label, isSoc, median, p25, p75}>` where `varyAxis` is `'care' | 'pn' | 'bp'`, `fixed` is `{[otherAxis]: level}` for the two non-varying axes, and the returned array always starts with the SOC row.
  - `notificationSeries(scenarios, {varyAxis, fixed}) -> array<{label, isSoc, over: {median,p25,p75}, under: {median,p25,p75}}>`

- [ ] **Step 1: Write the failing tests**

```js
// dashboard/src/utils/dataTransforms.test.js
import { describe, it, expect } from 'vitest';
import { quantile, medIqr, filterRows, getMetricValue, groupedSeries, notificationSeries } from './dataTransforms.js';

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
    diseases: { ng: { prev_end: 0.10, new_inf: 100, overtreatment_rate: 0.5, undertreatment_rate: 0.4 } },
    notification: { over_notification_rate: 0.5, under_notification_rate: 0.3 } },
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, draw: 2,
    diseases: { ng: { prev_end: 0.12, new_inf: 110, overtreatment_rate: 0.6, undertreatment_rate: 0.5 } },
    notification: { over_notification_rate: 0.6, under_notification_rate: 0.4 } },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.08, new_inf: 90, overtreatment_rate: 0.3, undertreatment_rate: 0.2 } },
    notification: { over_notification_rate: 0.3, under_notification_rate: 0.2 } },
  { care_level: 'baseline', pn_level: 'moderate', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.06, new_inf: 80, overtreatment_rate: 0.2, undertreatment_rate: 0.1 } },
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

describe('groupedSeries', () => {
  it('prepends a SOC entry, then one entry per level of the varying axis', () => {
    const result = groupedSeries(MOCK_ROWS, {
      varyAxis: 'pn', disease: 'ng', metric: 'prevalence',
      fixed: { care_level: 'baseline', bp_level: 'none' },
      levels: ['baseline', 'low', 'moderate', 'high'],
    });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true, median: 0.11 });
    expect(result.find(r => r.label === 'low')).toMatchObject({ median: 0.08 });
    expect(result.find(r => r.label === 'moderate')).toMatchObject({ median: 0.06 });
    // 'high' has no matching rows in the mock data -> median null, not thrown
    expect(result.find(r => r.label === 'high')).toMatchObject({ median: null });
  });
});

describe('notificationSeries', () => {
  it('returns SOC plus one entry per level, each with over and under sub-series', () => {
    const result = notificationSeries(MOCK_ROWS, {
      varyAxis: 'pn',
      fixed: { care_level: 'baseline', bp_level: 'none' },
      levels: ['baseline', 'low', 'moderate', 'high'],
    });
    expect(result[0].label).toBe('SOC');
    expect(result[0].over.median).toBeCloseTo(0.55, 5);
    expect(result.find(r => r.label === 'low').under.median).toBe(0.2);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd dashboard && npx vitest run`
Expected: FAIL — `Cannot find module './dataTransforms.js'` (or similar, since the file doesn't exist yet).

- [ ] **Step 3: Write `dashboard/src/utils/dataTransforms.js`**

```js
export function quantile(sortedArr, q) {
  const pos = (sortedArr.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sortedArr[base + 1] !== undefined) {
    return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base]);
  }
  return sortedArr[base];
}

export function medIqr(values) {
  const nums = values.filter((v) => v !== null && v !== undefined && !Number.isNaN(v))
    .slice().sort((a, b) => a - b);
  if (nums.length === 0) return { median: null, p25: null, p75: null };
  return {
    median: quantile(nums, 0.5),
    p25: quantile(nums, 0.25),
    p75: quantile(nums, 0.75),
  };
}

export function filterRows(scenarios, filters) {
  return scenarios.filter((row) =>
    Object.entries(filters).every(([key, value]) => value === undefined || row[key] === value)
  );
}

export function getMetricValue(row, { disease, metric }) {
  const d = row.diseases[disease];
  if (!d) return null;
  switch (metric) {
    case 'prevalence': return d.prev_end;
    case 'new_inf': return d.new_inf;
    case 'overtreatment': return d.overtreatment_rate;
    case 'undertreatment': return d.undertreatment_rate;
    default: throw new Error(`Unknown metric: ${metric}`);
  }
}

const AXIS_TO_FIELD = { care: 'care_level', pn: 'pn_level', bp: 'bp_level' };

export function groupedSeries(scenarios, { varyAxis, disease, metric, fixed, levels }) {
  const varyField = AXIS_TO_FIELD[varyAxis];
  const socRows = filterRows(scenarios, { poc: false });
  const soc = medIqr(socRows.map((r) => getMetricValue(r, { disease, metric })));
  const entries = levels.map((level) => {
    const rows = filterRows(scenarios, { poc: true, [varyField]: level, ...fixed });
    const stats = medIqr(rows.map((r) => getMetricValue(r, { disease, metric })));
    return { label: level, isSoc: false, ...stats };
  });
  return [{ label: 'SOC', isSoc: true, ...soc }, ...entries];
}

export function notificationSeries(scenarios, { varyAxis, fixed, levels }) {
  const varyField = AXIS_TO_FIELD[varyAxis];
  const socRows = filterRows(scenarios, { poc: false });
  const socOver = medIqr(socRows.map((r) => r.notification.over_notification_rate));
  const socUnder = medIqr(socRows.map((r) => r.notification.under_notification_rate));
  const entries = levels.map((level) => {
    const rows = filterRows(scenarios, { poc: true, [varyField]: level, ...fixed });
    return {
      label: level,
      isSoc: false,
      over: medIqr(rows.map((r) => r.notification.over_notification_rate)),
      under: medIqr(rows.map((r) => r.notification.under_notification_rate)),
    };
  });
  return [{ label: 'SOC', isSoc: true, over: socOver, under: socUnder }, ...entries];
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd dashboard && npx vitest run`
Expected: PASS, all 8 tests green.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/utils/dataTransforms.js dashboard/src/utils/dataTransforms.test.js
git commit -m "dashboard: add dataTransforms with unit tests"
```

---

## Task 4: Controls — DiseaseSelect, MetricTabs, LadderLevelSelect

**Files:**
- Create: `dashboard/src/components/controls/DiseaseSelect.jsx`
- Create: `dashboard/src/components/controls/MetricTabs.jsx`
- Create: `dashboard/src/components/controls/LadderLevelSelect.jsx`

**Interfaces:**
- Produces:
  - `DiseaseSelect({ value, onChange, disabled })` — pill group over `['hiv','ng','ct','tv','syph']` with display labels.
  - `MetricTabs({ value, onChange })` — tab group over `['prevalence','new_inf','overtreatment','undertreatment','notification']`.
  - `LadderLevelSelect({ label, levels, value, onChange })` — pill group over an arbitrary list of level strings; used both for the vary-axis picker (levels = `['care','pn','bp']`) and the two fixed-level pickers (levels = that axis's ladder levels).

- [ ] **Step 1: Create `dashboard/src/components/controls/DiseaseSelect.jsx`**

```jsx
const LABELS = { hiv: 'HIV', ng: 'Gonorrhoea', ct: 'Chlamydia', tv: 'Trichomoniasis', syph: 'Syphilis' };
const DISEASES = ['hiv', 'ng', 'ct', 'tv', 'syph'];

export default function DiseaseSelect({ value, onChange, disabled = false }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-brand-gray mr-1">Disease:</span>
      {DISEASES.map((d) => (
        <button
          key={d}
          disabled={disabled}
          onClick={() => onChange(d)}
          className={`px-3 py-1 rounded-full text-sm border-2 transition-colors ${
            disabled ? 'opacity-40 cursor-not-allowed border-gray-200 text-gray-400' :
            value === d ? 'bg-brand-teal border-brand-teal text-white' : 'border-brand-teal text-brand-teal'
          }`}
        >
          {LABELS[d]}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `dashboard/src/components/controls/MetricTabs.jsx`**

```jsx
const METRICS = [
  { key: 'prevalence', label: 'Prevalence' },
  { key: 'new_inf', label: 'New infections' },
  { key: 'overtreatment', label: 'Overtreatment' },
  { key: 'undertreatment', label: 'Undertreatment' },
  { key: 'notification', label: 'PN over/under-notification' },
];

export default function MetricTabs({ value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
      {METRICS.map((m) => (
        <button
          key={m.key}
          onClick={() => onChange(m.key)}
          className={`px-3 py-1.5 text-sm rounded-md ${
            value === m.key ? 'bg-brand-teal text-white' : 'text-brand-gray hover:bg-brand-grayLight'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create `dashboard/src/components/controls/LadderLevelSelect.jsx`**

```jsx
export default function LadderLevelSelect({ label, levels, value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-brand-gray mr-1">{label}:</span>
      {levels.map((level) => (
        <button
          key={level}
          onClick={() => onChange(level)}
          className={`px-3 py-1 rounded-full text-sm border-2 capitalize transition-colors ${
            value === level ? 'bg-brand-blue border-brand-blue text-white' : 'border-brand-blue text-brand-blue'
          }`}
        >
          {level}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Verify the app still builds (no consumers yet, but must not break the build)**

Run: `cd dashboard && npm run build`
Expected: succeeds (unused-file warnings, if any, are not build errors under this Vite config).

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/controls/
git commit -m "dashboard: add DiseaseSelect, MetricTabs, LadderLevelSelect controls"
```

---

## Task 5: `MetricChart.jsx`

**Files:**
- Create: `dashboard/src/components/sections/MetricChart.jsx`

**Interfaces:**
- Consumes: the array shape from `groupedSeries`/`notificationSeries` (Task 3).
- Produces: `MetricChart({ data, mode, yLabel })` where `mode` is `'single'` (data items have `{label, median, p25, p75}`) or `'notification'` (data items have `{label, over: {...}, under: {...}}`). Renders a Recharts bar chart with median bars and p25–p75 error bars, SOC's bar in `--brand-soc` gray, POC-arm bars in `--brand-teal`/`--brand-blue`.

- [ ] **Step 1: Create `dashboard/src/components/sections/MetricChart.jsx`**

```jsx
import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts';

const SOC_COLOR = '#555555';
const SERIES_COLORS = { median: '#0E7490', over: '#B35806', under: '#2E86C1' };

function withErrorBar(row, key) {
  const lo = row[`${key}`]?.p25 ?? row.p25;
  const hi = row[`${key}`]?.p75 ?? row.p75;
  const med = row[`${key}`]?.median ?? row.median;
  return { median: med, errorRange: med == null || lo == null || hi == null ? null : [med - lo, hi - med] };
}

export default function MetricChart({ data, mode = 'single', yLabel }) {
  if (mode === 'single') {
    const chartData = data.map((row) => ({
      label: row.label,
      isSoc: row.isSoc,
      median: row.median,
      errorRange: row.median == null || row.p25 == null || row.p75 == null
        ? null : [row.median - row.p25, row.p75 - row.median],
    }));
    return (
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
          <Bar dataKey="median" maxBarSize={60}>
            {chartData.map((row) => <Cell key={row.label} fill={row.isSoc ? SOC_COLOR : SERIES_COLORS.median} />)}
            <ErrorBar dataKey="errorRange" width={4} strokeWidth={1.5} stroke="#333" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  const chartData = data.map((row) => ({
    label: row.label,
    isSoc: row.isSoc,
    ...withErrorBar(row, 'over'),
    overMedian: row.over.median,
    overRange: row.over.median == null || row.over.p25 == null || row.over.p75 == null
      ? null : [row.over.median - row.over.p25, row.over.p75 - row.over.median],
    underMedian: row.under.median,
    underRange: row.under.median == null || row.under.p25 == null || row.under.p75 == null
      ? null : [row.under.median - row.under.p25, row.under.p75 - row.under.median],
  }));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
        <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
        <Legend />
        <Bar dataKey="overMedian" name="Over-notification" fill={SERIES_COLORS.over} maxBarSize={40}>
          <ErrorBar dataKey="overRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
        <Bar dataKey="underMedian" name="Under-notification" fill={SERIES_COLORS.under} maxBarSize={40}>
          <ErrorBar dataKey="underRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/MetricChart.jsx
git commit -m "dashboard: add generic MetricChart (single-series and notification modes)"
```

---

## Task 6: `ScenarioExplorer.jsx`

**Files:**
- Create: `dashboard/src/components/sections/ScenarioExplorer.jsx`

**Interfaces:**
- Consumes: `src/data/scenarios.json`, `src/data/ladders.json`, `groupedSeries`/`notificationSeries` (Task 3), `DiseaseSelect`/`MetricTabs`/`LadderLevelSelect` (Task 4), `MetricChart` (Task 5).
- Produces: `<ScenarioExplorer />`, a self-contained section with no props (reads its own data imports), rendered by `App.jsx` in Task 8.

- [ ] **Step 1: Create `dashboard/src/components/sections/ScenarioExplorer.jsx`**

```jsx
import { useState, useMemo } from 'react';
import scenarios from '../../data/scenarios.json';
import ladders from '../../data/ladders.json';
import { groupedSeries, notificationSeries } from '../../utils/dataTransforms.js';
import DiseaseSelect from '../controls/DiseaseSelect.jsx';
import MetricTabs from '../controls/MetricTabs.jsx';
import LadderLevelSelect from '../controls/LadderLevelSelect.jsx';
import MetricChart from './MetricChart.jsx';

const AXES = ['care', 'pn', 'bp'];
const AXIS_LABELS = { care: 'Care-seeking', pn: 'PN intensity', bp: 'Bundled prevention' };
const AXIS_TO_FIELD = { care: 'care_level', pn: 'pn_level', bp: 'bp_level' };
const DEFAULT_LEVEL = { care: 'baseline', pn: 'moderate', bp: 'moderate' };

const Y_LABELS = {
  prevalence: 'End-of-horizon prevalence',
  new_inf: 'New infections (cumulative)',
  overtreatment: 'Overtreatment rate',
  undertreatment: 'Undertreatment rate',
  notification: 'Rate',
};

export default function ScenarioExplorer() {
  const [disease, setDisease] = useState('ng');
  const [metric, setMetric] = useState('prevalence');
  const [varyAxis, setVaryAxis] = useState('pn');
  const [fixedLevel, setFixedLevel] = useState(DEFAULT_LEVEL);

  const otherAxes = AXES.filter((a) => a !== varyAxis);

  const fixed = useMemo(() => {
    const result = {};
    for (const axis of otherAxes) result[AXIS_TO_FIELD[axis]] = fixedLevel[axis];
    return result;
  }, [otherAxes, fixedLevel]);

  const chartData = useMemo(() => {
    const levels = ladders[varyAxis].levels;
    if (metric === 'notification') {
      return notificationSeries(scenarios, { varyAxis, fixed, levels });
    }
    return groupedSeries(scenarios, { varyAxis, disease, metric, fixed, levels });
  }, [varyAxis, disease, metric, fixed]);

  return (
    <section id="explorer" className="py-16 bg-brand-grayLight">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-2">Scenario explorer</h2>
        <p className="text-brand-gray mb-6 max-w-2xl">
          Explore the full 65-cell scenario factorial: pick which lever varies along the
          x-axis, hold the other two fixed, and choose a disease and outcome. SOC (no POC,
          no added levers) is always shown as the gray reference bar.
        </p>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-6 space-y-3">
          <MetricTabs value={metric} onChange={setMetric} />
          <DiseaseSelect value={disease} onChange={setDisease} disabled={metric === 'notification'} />
          <LadderLevelSelect label="Vary" levels={AXES} value={varyAxis} onChange={setVaryAxis} />
          {otherAxes.map((axis) => (
            <LadderLevelSelect
              key={axis}
              label={`Fixed: ${AXIS_LABELS[axis]}`}
              levels={ladders[axis].levels}
              value={fixedLevel[axis]}
              onChange={(level) => setFixedLevel((prev) => ({ ...prev, [axis]: level }))}
            />
          ))}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <MetricChart
            data={chartData}
            mode={metric === 'notification' ? 'notification' : 'single'}
            yLabel={Y_LABELS[metric]}
          />
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Manual smoke test**

Run: `cd dashboard && npm run dev`, open the printed localhost URL.
Expected: a chart renders with a "SOC" bar plus 4 POC-level bars; switching `varyAxis`, `metric`, and `disease` all change the chart without console errors. Switching to the "PN over/under-notification" metric disables the disease selector and shows two bars per level.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/ScenarioExplorer.jsx
git commit -m "dashboard: add ScenarioExplorer section"
```

---

## Task 7: `Overview.jsx`

**Files:**
- Create: `dashboard/src/components/sections/Overview.jsx`

**Interfaces:**
- Consumes: `src/data/diagnostic_performance.json`.
- Produces: `<Overview />`.

- [ ] **Step 1: Create `dashboard/src/components/sections/Overview.jsx`**

```jsx
import diagnosticPerformance from '../../data/diagnostic_performance.json';

const DISEASE_ORDER = ['Gonorrhoea', 'Chlamydia', 'Trichomoniasis', 'Syphilis'];

function pct(v) {
  return v == null ? '—' : `${(v * 100).toFixed(0)}%`;
}

export default function Overview() {
  return (
    <section id="overview" className="py-16">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-brand-blue mb-4">
          Estimating the health impact of improved STI diagnostics
        </h1>
        <p className="text-brand-gray mb-6">
          Most curable STIs in women are asymptomatic — the largest drop-off in the cascade
          from infection to cure. Downstream drop-offs are smaller but more intervenable:
          symptomatic care-seeking can be increased through demand generation and partner
          notification; correct treatment rates can be improved by point-of-care (POC)
          diagnostics; 12-month cure rates can be improved by partner notification and
          bundled prevention. This dashboard explores the modeled health impact of all four
          levers, alone and combined, in a Zimbabwe-calibrated STIsim model.
        </p>
        <p className="text-brand-gray mb-8">
          Syndromic management can&apos;t distinguish between STIs, so treatment is
          symptom-based rather than infection-specific. POC diagnostics improve both
          sensitivity and specificity, but at the prevalences seen among women presenting
          with vaginal discharge syndrome, even a highly performant test leaves a meaningful
          share of false positives — POC narrows the overtreatment gap without closing it.
        </p>

        <h2 className="text-lg font-semibold text-brand-blue mb-3">
          Diagnostic performance, SOC vs POC
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border border-gray-200">
            <thead className="bg-brand-grayLight">
              <tr>
                <th className="p-2 text-left">Disease</th>
                <th className="p-2 text-left">Arm</th>
                <th className="p-2 text-right">Prevalence*</th>
                <th className="p-2 text-right">Sensitivity</th>
                <th className="p-2 text-right">Specificity</th>
                <th className="p-2 text-right">PPV</th>
                <th className="p-2 text-right">NPV</th>
              </tr>
            </thead>
            <tbody>
              {DISEASE_ORDER.flatMap((disease) =>
                diagnosticPerformance
                  .filter((r) => r.disease === disease)
                  .map((r) => (
                    <tr key={`${r.disease}-${r.arm}`} className="border-t border-gray-100">
                      <td className="p-2">{r.disease}</td>
                      <td className="p-2">{r.arm}</td>
                      <td className="p-2 text-right">{pct(r.prev)}</td>
                      <td className="p-2 text-right">{pct(r.sens)}</td>
                      <td className="p-2 text-right">{pct(r.spec)}</td>
                      <td className="p-2 text-right">{pct(r.PPV)}</td>
                      <td className="p-2 text-right">{pct(r.NPV)}</td>
                    </tr>
                  ))
              )}
            </tbody>
          </table>
          <p className="text-xs text-brand-gray mt-2">* Among women presenting with vaginal discharge syndrome.</p>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/Overview.jsx
git commit -m "dashboard: add Overview section with SOC-vs-POC diagnostic performance table"
```

---

## Task 8: `KeyFindings.jsx`

**Files:**
- Create: `dashboard/src/components/sections/KeyFindings.jsx`

**Interfaces:**
- Consumes: `src/data/scenarios.json`, `filterRows`/`medIqr` (Task 3).
- Produces: `<KeyFindings />`.

- [ ] **Step 1: Create `dashboard/src/components/sections/KeyFindings.jsx`**

```jsx
import scenarios from '../../data/scenarios.json';
import { filterRows, medIqr, getMetricValue } from '../../utils/dataTransforms.js';

function medianOf(rows, fn) {
  return medIqr(rows.map(fn)).median;
}

function pct(v) {
  return v == null ? '—' : `${(v * 100).toFixed(0)}%`;
}

function FindingCard({ number, title, children }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <p className="text-xs font-semibold uppercase tracking-widest text-brand-teal mb-1">
        Result {number}
      </p>
      <h3 className="font-semibold text-brand-blue mb-2">{title}</h3>
      <div className="text-sm text-brand-gray space-y-1">{children}</div>
    </div>
  );
}

export default function KeyFindings() {
  const soc = filterRows(scenarios, { poc: false });
  const pocAlone = filterRows(scenarios, { poc: true, care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' });
  const pocPnHigh = filterRows(scenarios, { poc: true, care_level: 'baseline', pn_level: 'high', bp_level: 'none' });
  const pocBpHigh = filterRows(scenarios, { poc: true, care_level: 'baseline', pn_level: 'moderate', bp_level: 'high' });
  const pocCareHigh = filterRows(scenarios, { poc: true, care_level: 'high', pn_level: 'moderate', bp_level: 'moderate' });

  const ngOvertreat = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'ng', metric: 'overtreatment' })),
    poc: medianOf(pocAlone, (r) => getMetricValue(r, { disease: 'ng', metric: 'overtreatment' })),
  };
  const syphOvertreat = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'syph', metric: 'overtreatment' })),
    poc: medianOf(pocAlone, (r) => getMetricValue(r, { disease: 'syph', metric: 'overtreatment' })),
  };
  const overNotif = {
    soc: medianOf(soc, (r) => r.notification.over_notification_rate),
    poc: medianOf(pocAlone, (r) => r.notification.over_notification_rate),
  };
  const ngPrevPocAlone = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'ng', metric: 'prevalence' })),
    poc: medianOf(pocAlone, (r) => getMetricValue(r, { disease: 'ng', metric: 'prevalence' })),
  };
  const ngPrevPn = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'ng', metric: 'prevalence' })),
    poc: medianOf(pocPnHigh, (r) => getMetricValue(r, { disease: 'ng', metric: 'prevalence' })),
  };
  const ngNewInfPn = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'ng', metric: 'new_inf' })),
    poc: medianOf(pocPnHigh, (r) => getMetricValue(r, { disease: 'ng', metric: 'new_inf' })),
  };
  const syphPrevBp = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'syph', metric: 'prevalence' })),
    poc: medianOf(pocBpHigh, (r) => getMetricValue(r, { disease: 'syph', metric: 'prevalence' })),
  };
  const syphNewInfBp = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'syph', metric: 'new_inf' })),
    poc: medianOf(pocBpHigh, (r) => getMetricValue(r, { disease: 'syph', metric: 'new_inf' })),
  };
  const tvPrevCare = {
    soc: medianOf(soc, (r) => getMetricValue(r, { disease: 'tv', metric: 'prevalence' })),
    poc: medianOf(pocCareHigh, (r) => getMetricValue(r, { disease: 'tv', metric: 'prevalence' })),
  };

  return (
    <section id="findings" className="py-16">
      <div className="max-w-5xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-6">Key findings</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FindingCard number={1} title="POC diagnostics cut overtreatment and unwarranted notification, but don't eliminate them">
            <p>Gonorrhoea overtreatment: {pct(ngOvertreat.soc)} (SOC) → {pct(ngOvertreat.poc)} (POC alone)</p>
            <p>Syphilis overtreatment: {pct(syphOvertreat.soc)} (SOC) → {pct(syphOvertreat.poc)} (POC alone)</p>
            <p>Unwarranted partner notification: {pct(overNotif.soc)} (SOC) → {pct(overNotif.poc)} (POC alone)</p>
          </FindingCard>
          <FindingCard number={2} title="POC diagnostics alone do not reduce prevalence or incidence">
            <p>Gonorrhoea prevalence, POC alone vs SOC: {pct(ngPrevPocAlone.poc)} vs {pct(ngPrevPocAlone.soc)}</p>
            <p>Short reinfection cycles offset diagnostic gains without an added prevention or notification lever.</p>
          </FindingCard>
          <FindingCard number={3} title="POC + high-intensity partner notification lowers prevalence, but incidence stays high">
            <p>Gonorrhoea prevalence: {pct(ngPrevPn.soc)} (SOC) → {pct(ngPrevPn.poc)} (POC + high PN)</p>
            <p>Gonorrhoea new infections: {Math.round(ngNewInfPn.soc ?? 0).toLocaleString()} (SOC) → {Math.round(ngNewInfPn.poc ?? 0).toLocaleString()} (POC + high PN)</p>
          </FindingCard>
          <FindingCard number={4} title="POC + bundled prevention bends both prevalence and incidence">
            <p>Syphilis prevalence: {pct(syphPrevBp.soc)} (SOC) → {pct(syphPrevBp.poc)} (POC + moderate PN + high bundled prevention)</p>
            <p>Syphilis new infections: {Math.round(syphNewInfBp.soc ?? 0).toLocaleString()} (SOC) → {Math.round(syphNewInfBp.poc ?? 0).toLocaleString()}</p>
          </FindingCard>
          <FindingCard number={5} title="Adding demand generation pushes trichomoniasis, syphilis, and chlamydia toward elimination">
            <p>Trichomoniasis prevalence: {pct(tvPrevCare.soc)} (SOC) → {pct(tvPrevCare.poc)} (all four levers, high care-seeking)</p>
          </FindingCard>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Manual check**

Run: `npm run dev`, view the KeyFindings section.
Expected: all 5 cards render real percentages/numbers (not "—" or `NaN`) — confirms the lever combinations chosen (`pn_level: 'high'`, `bp_level: 'high'`, etc.) actually exist among the 65 cells and produce non-empty row sets.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/KeyFindings.jsx
git commit -m "dashboard: add KeyFindings section with live-computed stats"
```

---

## Task 9: `Methods.jsx`, `Header.jsx`, `Footer.jsx`

**Files:**
- Create: `dashboard/src/components/sections/Methods.jsx`
- Create: `dashboard/src/components/layout/Header.jsx`
- Create: `dashboard/src/components/layout/Footer.jsx`

**Interfaces:**
- Produces: `<Methods />`, `<Header />`, `<Footer />` — all self-contained, no props.

- [ ] **Step 1: Create `dashboard/src/components/sections/Methods.jsx`**

```jsx
import { useState } from 'react';

const ITEMS = [
  {
    title: 'Model',
    body: `STIsim simulation of HIV, syphilis, gonorrhoea (NG), chlamydia (CT), trichomoniasis
      (TV), and bacterial vaginosis (BV) in Zimbabwe, with structured sexual networks and
      partner-notification edges. The custom slot wires a FetalHealth connector for adverse
      pregnancy and birth outcomes.`,
  },
  {
    title: 'Calibration',
    body: `500-draw Latin hypercube sample over 17 open parameters (disease betas, HIV–syphilis
      coupling, network structure, syphilis natural history), K=5 seed-averaged per draw,
      scored by continuous weighted goodness-of-fit against Zimbabwe HIV/STI prevalence data
      and ZIMPHIA age-by-sex syphilis tables. The top-30 draws by fit form the posterior
      ensemble used throughout this dashboard — results always reflect that ensemble's spread,
      not a single point estimate.`,
  },
  {
    title: 'Scenario design',
    body: `Three intensity ladders (care-seeking, partner-notification, bundled prevention),
      each with 4 levels, layered on a standard-of-care (SOC) vs point-of-care (POC)
      diagnostics factorial — 65 cells total (SOC + 4×4×4 POC combinations), each run across
      the full posterior ensemble. Ladders diverge from SOC-equivalent levels only from the
      2027 intervention year onward.`,
  },
];

function AccordionItem({ title, body, open, onToggle }) {
  return (
    <div className="border-b border-gray-200">
      <button onClick={onToggle} className="w-full text-left py-3 flex justify-between items-center">
        <span className="font-medium text-brand-blue">{title}</span>
        <span className="text-brand-gray">{open ? '−' : '+'}</span>
      </button>
      {open && <p className="pb-4 text-sm text-brand-gray">{body}</p>}
    </div>
  );
}

export default function Methods() {
  const [openIndex, setOpenIndex] = useState(0);
  return (
    <section id="methods" className="py-16 bg-brand-grayLight">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-6">Methods</h2>
        {ITEMS.map((item, i) => (
          <AccordionItem
            key={item.title}
            title={item.title}
            body={item.body}
            open={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create `dashboard/src/components/layout/Header.jsx`**

```jsx
export default function Header() {
  return (
    <header className="sticky top-0 bg-white border-b border-gray-200 z-10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <span className="font-semibold text-brand-blue">STI Notification — Scenario Dashboard</span>
        <nav className="flex gap-4 text-sm text-brand-gray">
          <a href="#overview" className="hover:text-brand-teal">Overview</a>
          <a href="#explorer" className="hover:text-brand-teal">Explorer</a>
          <a href="#findings" className="hover:text-brand-teal">Findings</a>
          <a href="#methods" className="hover:text-brand-teal">Methods</a>
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Create `dashboard/src/components/layout/Footer.jsx`**

```jsx
export default function Footer() {
  return (
    <footer className="border-t border-gray-200 py-6">
      <div className="max-w-5xl mx-auto px-4 text-xs text-brand-gray">
        sti_notification project — Institute for Disease Modeling. Source code and data export
        pipeline in this repository.
      </div>
    </footer>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/components/sections/Methods.jsx dashboard/src/components/layout/
git commit -m "dashboard: add Methods accordion, Header, Footer"
```

---

## Task 10: Assemble `App.jsx` and final verification

**Files:**
- Modify: `dashboard/src/App.jsx`

**Interfaces:**
- Consumes: `Header`, `Footer` (Task 9), `Overview` (Task 7), `ScenarioExplorer` (Task 6), `KeyFindings` (Task 8), `Methods` (Task 9).

- [ ] **Step 1: Rewrite `dashboard/src/App.jsx`**

```jsx
import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import Overview from './components/sections/Overview.jsx';
import ScenarioExplorer from './components/sections/ScenarioExplorer.jsx';
import KeyFindings from './components/sections/KeyFindings.jsx';
import Methods from './components/sections/Methods.jsx';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <Header />
      <main className="flex-1">
        <Overview />
        <ScenarioExplorer />
        <KeyFindings />
        <Methods />
      </main>
      <Footer />
    </div>
  );
}
```

- [ ] **Step 2: Run the full test suite**

Run: `cd dashboard && npx vitest run`
Expected: all `dataTransforms.test.js` tests pass.

- [ ] **Step 3: Run the production build**

Run: `cd dashboard && npm run build`
Expected: succeeds, no console warnings about missing data imports.

- [ ] **Step 4: Manual end-to-end check**

Run: `cd dashboard && npm run preview`, open the printed URL.
Expected: Overview, Scenario Explorer, Key Findings, and Methods sections all render with real data (no "—" placeholders in KeyFindings, no empty charts in the explorer for the default disease/metric/axis selection). Click through Header nav links — each scrolls to the corresponding section. Toggle every value of `varyAxis`, `metric`, and `disease` at least once with no console errors.

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/App.jsx
git commit -m "dashboard: assemble Overview, ScenarioExplorer, KeyFindings, Methods in App"
```

---

## Self-review notes

- **Spec coverage:** Overview (Task 7), ScenarioExplorer exposing the full 65-cell factorial (Task 6), KeyFindings computed live (Task 8), Methods (Task 9) — all four approved sections present. Data pipeline (Task 2) covers `scenarios.kavg.csv` and `slide4_diagnostic_performance.csv`; `ppv_table.csv`/`specificity.csv` deliberately dropped, documented in Global Constraints. Ladder labels imported from `scenarios.py`, never hardcoded (Task 2, Step 1). Deployment and CI wiring explicitly out of scope, matching the spec.
- **Undertreatment/under-notification formulas**, flagged as open in the spec, are pinned down concretely in Task 2 and re-used consistently in `dataTransforms.js` (Task 3) and `KeyFindings.jsx` (Task 8) — no remaining ambiguity.
- **Type/name consistency check:** `care_level`/`pn_level`/`bp_level` (Task 2's export) match `AXIS_TO_FIELD` in both `dataTransforms.js` (Task 3) and `ScenarioExplorer.jsx` (Task 6). `getMetricValue`'s metric keys (`prevalence`/`new_inf`/`overtreatment`/`undertreatment`) match `MetricTabs`' keys (Task 4) and `Y_LABELS` (Task 6). `groupedSeries`/`notificationSeries` signatures defined in Task 3 match their call sites in Task 6 exactly (same argument names: `varyAxis`, `disease`, `metric`, `fixed`, `levels`).
