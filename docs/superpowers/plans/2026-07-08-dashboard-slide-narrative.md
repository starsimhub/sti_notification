# Dashboard Slide-Narrative Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the dashboard's opening narrative into four sections that follow the slide deck's story (the problem, how POC diagnostics help, a hypothesis about what else could help, results for combined strategies), embedding static slide figures where illustrative and rebuilding SOC-vs-scenario comparisons as interactive, toggleable charts driven by real data.

**Architecture:** Two new shared components (`PresetToggleGroup` for checkbox toggling of named scenario presets, and a pure `filterPresetSeries` utility) let four new section components compose the dashboard's existing, unchanged `dataTransforms.js` functions and `MetricChart.jsx` modes into interactive preset comparisons — no changes to either file. `Overview.jsx`/`KeyFindings.jsx` are replaced; `ScenarioExplorer.jsx`/`Methods.jsx`/`MetricChart.jsx`/`dataTransforms.js` are otherwise untouched (Methods gets a content-only fix).

**Tech Stack:** Same as the existing dashboard — React 18, Vite 5, Tailwind CSS 3, Recharts 2, Vitest.

## Global Constraints

- Diseases: `ng`, `ct`, `tv`, `syph` only — HIV stays excluded everywhere.
- No changes to `dataTransforms.js`, `MetricChart.jsx`, or `ScenarioExplorer.jsx` — all new interactivity composes these unchanged.
- SOC always renders in `SOC_COLOR` (gray); other series cycle `MetricChart`'s existing `PALETTE` by index — this is automatic as long as new components pass data through `MetricChart` unmodified.
- `fig_slide5/6/9/10/11.png` are NOT embedded as static images anywhere — fully superseded by interactive charts.
- `fig_slide5.png`'s VDS-treatment, GUD-treatment, and female→male-notification-cascade panels are out of scope (no corresponding data in `scenarios.json`).
- Images are imported via ES `import` into `dashboard/src/assets/figures/`, not a `public/` directory.
- `Overview.jsx` and `KeyFindings.jsx` must be deleted, not left unused.

---

## Task 1: `filterPresetSeries` utility, with TDD tests

**Files:**
- Create: `dashboard/src/utils/presetFilters.js`
- Test: `dashboard/src/utils/presetFilters.test.js`

**Interfaces:**
- Consumes: nothing (pure function, no dependency on other tasks).
- Produces: `filterPresetSeries(series, presets, selectedKeys) -> array` — used by every later section/component task in this plan. `series` is the array returned by `crossProductBarSeries`/`crossProductNotificationSeries`/`timeSeriesForCombos` (each entry has at least `{label, isSoc, ...}`). `presets` is `[{key, label, ...levels}]`. `selectedKeys` is `string[]`. Returns the subset of `series` whose `label` matches a preset whose `key` is in `selectedKeys`, in `series`'s original order (not `selectedKeys`'s order).

- [ ] **Step 1: Write the failing tests**

Create `dashboard/src/utils/presetFilters.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { filterPresetSeries } from './presetFilters.js';

const PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
  { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' },
];

const SERIES = [
  { label: 'SOC', isSoc: true, median: 0.1 },
  { label: 'POC alone', isSoc: false, median: 0.08 },
  { label: 'POC + PN high', isSoc: false, median: 0.05 },
];

describe('filterPresetSeries', () => {
  it('returns only the series entries whose label matches a selected preset key', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['soc', 'pn_high']);
    expect(result).toEqual([
      { label: 'SOC', isSoc: true, median: 0.1 },
      { label: 'POC + PN high', isSoc: false, median: 0.05 },
    ]);
  });

  it('preserves the original series order, not the order keys were selected in', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['pn_high', 'soc']);
    expect(result.map((r) => r.label)).toEqual(['SOC', 'POC + PN high']);
  });

  it('returns an empty array when no keys are selected', () => {
    expect(filterPresetSeries(SERIES, PRESETS, [])).toEqual([]);
  });

  it('returns all entries when all keys are selected', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['soc', 'poc', 'pn_high']);
    expect(result).toHaveLength(3);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd dashboard && npx vitest run`
Expected: FAIL — `presetFilters.js` does not exist / `filterPresetSeries` is not exported.

- [ ] **Step 3: Implement `dashboard/src/utils/presetFilters.js`**

```js
export function filterPresetSeries(series, presets, selectedKeys) {
  const selectedLabels = new Set(
    presets.filter((p) => selectedKeys.includes(p.key)).map((p) => p.label)
  );
  return series.filter((s) => selectedLabels.has(s.label));
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd dashboard && npx vitest run`
Expected: PASS, all tests green (existing `dataTransforms.test.js` tests plus these 4 new ones).

- [ ] **Step 5: Commit**

```bash
git add dashboard/src/utils/presetFilters.js dashboard/src/utils/presetFilters.test.js
git commit -m "dashboard: add filterPresetSeries utility for preset-toggle charts"
```

---

## Task 2: `PresetToggleGroup.jsx` control

**Files:**
- Create: `dashboard/src/components/controls/PresetToggleGroup.jsx`

**Interfaces:**
- Consumes: nothing new (no dependency on Task 1).
- Produces: `PresetToggleGroup({ presets: [{key, label}], selected: string[], onChange })` — used by `OvertreatmentNotificationCompare` (Task 4) and `PresetTimeseriesCompare` (Task 5). Enforces "at least one preset stays checked" (clicking the last checked box is a no-op), mirroring `LadderCheckboxGroup`'s existing guard.

- [ ] **Step 1: Create `dashboard/src/components/controls/PresetToggleGroup.jsx`**

```jsx
export default function PresetToggleGroup({ presets, selected, onChange }) {
  function toggle(key) {
    if (selected.includes(key)) {
      if (selected.length === 1) return;
      onChange(selected.filter((k) => k !== key));
    } else {
      onChange([...selected, key]);
    }
  }
  return (
    <div className="flex items-center gap-3 flex-wrap mb-4">
      {presets.map(({ key, label }) => (
        <label
          key={key}
          className="flex items-center gap-1.5 text-sm text-brand-gray cursor-pointer"
        >
          <input
            type="checkbox"
            checked={selected.includes(key)}
            onChange={() => toggle(key)}
            className="accent-brand-blue"
          />
          {label}
        </label>
      ))}
    </div>
  );
}
```

No test file for this task — it's a presentational component with the same guard logic already covered by `LadderCheckboxGroup`'s precedent (no dedicated test in this codebase), and its one piece of real logic (the guard) is simple enough to verify by inspection; the filtering logic it feeds into is what Task 1 already tests.

- [ ] **Step 2: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds (this file isn't imported anywhere yet, so it can't break anything, but confirms no syntax errors).

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/controls/PresetToggleGroup.jsx
git commit -m "dashboard: add PresetToggleGroup control"
```

---

## Task 3: Section 1 — `TheProblem.jsx`

**Files:**
- Create: `dashboard/src/components/sections/TheProblem.jsx`
- Create (copy): `dashboard/src/assets/figures/fig_slide2.png`
- Create (copy): `dashboard/src/assets/figures/fig_slide3.png`
- Create (copy): `dashboard/src/assets/figures/fig_slide4.png`

**Interfaces:**
- Consumes: `dashboard/src/data/diagnostic_performance.json` (unchanged, same shape already used by `Overview.jsx`).
- Produces: `TheProblem()` — a section component with `id="problem"`, wired into `App.jsx` in Task 10. Not wired yet in this task; `Overview.jsx` (which it replaces) is not deleted until Task 10, so the app continues to build and run unaffected.

- [ ] **Step 1: Copy the three images into the dashboard's asset directory**

```bash
mkdir -p dashboard/src/assets/figures
cp figures/fig_slide2.png dashboard/src/assets/figures/fig_slide2.png
cp figures/fig_slide3.png dashboard/src/assets/figures/fig_slide3.png
cp figures/fig_slide4.png dashboard/src/assets/figures/fig_slide4.png
```

- [ ] **Step 2: Create `dashboard/src/components/sections/TheProblem.jsx`**

```jsx
import diagnosticPerformance from '../../data/diagnostic_performance.json';
import figSlide2 from '../../assets/figures/fig_slide2.png';
import figSlide3 from '../../assets/figures/fig_slide3.png';
import figSlide4 from '../../assets/figures/fig_slide4.png';

const DISEASE_ORDER = ['Gonorrhoea', 'Chlamydia', 'Trichomoniasis', 'Syphilis'];

function pct(v) {
  return v == null ? '—' : `${(v * 100).toFixed(0)}%`;
}

export default function TheProblem() {
  return (
    <section id="problem" className="py-16">
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

        <img
          src={figSlide2}
          alt="Cascade from infection to cure, by disease"
          className="w-full border border-gray-200 rounded-lg mb-2"
        />
        <p className="text-xs text-brand-gray mb-8">
          Steps from model parameters (symptomatic, care-seeking 0.49, syndromic routing,
          cure). Reinfection: CT measured (50%); provisional elsewhere. Grey = lost at each
          step. Preliminary: draw 66, single seed.
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
        <div className="overflow-x-auto mb-8">
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

        <p className="text-brand-gray mb-2">
          The poor specificity of syndromic management leads to a sizable number of
          unnecessary treatments and unwarranted partner notifications.
        </p>
        <img
          src={figSlide3}
          alt="Syndromic management overtreatment and unwarranted partner notification"
          className="w-full border border-gray-200 rounded-lg mb-8"
        />

        <p className="text-brand-gray mb-2">
          Despite improvements in sensitivity and specificity, low prevalence means we
          should temper our expectations around the reduction in overtreatment.
        </p>
        <img
          src={figSlide4}
          alt="VDS etiology, 2030-40"
          className="w-full border border-gray-200 rounded-lg"
        />
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds, no errors (file is not yet imported by `App.jsx`, so this just confirms valid JSX/imports).

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/TheProblem.jsx dashboard/src/assets/figures/fig_slide2.png dashboard/src/assets/figures/fig_slide3.png dashboard/src/assets/figures/fig_slide4.png
git commit -m "dashboard: add Section 1 (TheProblem) with cascade/overtreatment/VDS figures"
```

---

## Task 4: `OvertreatmentNotificationCompare.jsx`

**Files:**
- Create: `dashboard/src/components/sections/OvertreatmentNotificationCompare.jsx`

**Interfaces:**
- Consumes: `crossProductBarSeries`, `crossProductNotificationSeries` (existing, unchanged, from `dataTransforms.js`); `filterPresetSeries` (Task 1); `PresetToggleGroup` (Task 2); `MetricChart` (existing, unchanged, `'single'` and `'notification'` modes); `dashboard/src/data/scenarios.json` (existing).
- Produces: `OvertreatmentNotificationCompare({ presets: [{key, label, care_level?, pn_level?, bp_level?}] })` — used once, by `ResultsHowPocHelps` (Task 6). `presets[0]` must be the SOC entry (`key: 'soc'`, no level fields); all other entries need all three level fields.

- [ ] **Step 1: Create `dashboard/src/components/sections/OvertreatmentNotificationCompare.jsx`**

```jsx
import { useState } from 'react';
import scenarios from '../../data/scenarios.json';
import { crossProductBarSeries, crossProductNotificationSeries } from '../../utils/dataTransforms.js';
import { filterPresetSeries } from '../../utils/presetFilters.js';
import PresetToggleGroup from '../controls/PresetToggleGroup.jsx';
import MetricChart from './MetricChart.jsx';

const DISEASES = [
  { key: 'ng', label: 'Gonorrhoea' },
  { key: 'ct', label: 'Chlamydia' },
  { key: 'tv', label: 'Trichomoniasis' },
  { key: 'syph', label: 'Syphilis' },
];

function combosFromPresets(presets) {
  return presets
    .filter((p) => p.key !== 'soc')
    .map((p) => ({ care_level: p.care_level, pn_level: p.pn_level, bp_level: p.bp_level, label: p.label }));
}

export default function OvertreatmentNotificationCompare({ presets }) {
  const [selected, setSelected] = useState(presets.map((p) => p.key));
  const combos = combosFromPresets(presets);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8">
      <PresetToggleGroup presets={presets} selected={selected} onChange={setSelected} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {DISEASES.map(({ key, label }) => {
          const series = crossProductBarSeries(scenarios, { combos, disease: key, metric: 'overtreatment' });
          const filtered = filterPresetSeries(series, presets, selected);
          return (
            <div key={key}>
              <h3 className="font-semibold text-brand-blue mb-3">{label}</h3>
              <MetricChart data={filtered} mode="single" yLabel="Overtreatment rate" />
            </div>
          );
        })}
      </div>
      <div>
        <h3 className="font-semibold text-brand-blue mb-3">Partner notification</h3>
        <MetricChart
          data={filterPresetSeries(crossProductNotificationSeries(scenarios, { combos }), presets, selected)}
          mode="notification"
          yLabel="Rate"
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Manually verify the data path with a throwaway script**

Run (from `dashboard/`, using the `starsim` conda env's `node` is not needed — this is a `node` script, not Python; use whatever `node` is on `PATH`, the same one `npm` uses):

```bash
cd dashboard
cat > /tmp/verify-task4.mjs << 'EOF'
import scenarios from './src/data/scenarios.json' with { type: 'json' };
import { crossProductBarSeries, crossProductNotificationSeries } from './src/utils/dataTransforms.js';
import { filterPresetSeries } from './src/utils/presetFilters.js';

const presets = [
  { key: 'soc', label: 'SOC' },
  { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
];
const combos = [{ care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', label: 'POC alone' }];

for (const disease of ['ng', 'ct', 'tv', 'syph']) {
  const series = crossProductBarSeries(scenarios, { combos, disease, metric: 'overtreatment' });
  const filtered = filterPresetSeries(series, presets, ['soc', 'poc']);
  console.log(disease, filtered.map((r) => [r.label, r.median]));
}
const notif = crossProductNotificationSeries(scenarios, { combos });
console.log('notification', filterPresetSeries(notif, presets, ['soc', 'poc']).map((r) => r.label));
console.log('toggle SOC off:', filterPresetSeries(
  crossProductBarSeries(scenarios, { combos, disease: 'ng', metric: 'overtreatment' }), presets, ['poc']
).map((r) => r.label));
EOF
node /tmp/verify-task4.mjs
rm /tmp/verify-task4.mjs
```

Expected: for each of the 4 diseases, two `[label, median]` pairs with non-null numeric medians (`SOC` and `POC alone`); the notification line lists both labels; the "toggle SOC off" line lists only `['POC alone']`.

Report the exact output in your report file — this is the evidence the filtering logic and the component's data wiring are correct, since there's no automated test harness for React component rendering in this codebase.

- [ ] **Step 3: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds (file not yet imported by `App.jsx`).

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/OvertreatmentNotificationCompare.jsx
git commit -m "dashboard: add OvertreatmentNotificationCompare (SOC vs POC toggle)"
```

---

## Task 5: `PresetTimeseriesCompare.jsx`

**Files:**
- Create: `dashboard/src/components/sections/PresetTimeseriesCompare.jsx`

**Interfaces:**
- Consumes: `crossProductBarSeries`, `timeSeriesForCombos` (existing, unchanged, from `dataTransforms.js`); `filterPresetSeries` (Task 1); `PresetToggleGroup` (Task 2); `MetricChart` (existing, unchanged, `'single'` and `'timeseries'` modes); `dashboard/src/data/scenarios.json` and `dashboard/src/data/timeseries.json` (existing).
- Produces: `PresetTimeseriesCompare({ presets: [{key, label, care_level?, pn_level?, bp_level?}] })` — reused 4 times, by `ResultsHowPocHelps` (Task 6, once) and `ResultsCombinedStrategies` (Task 8, three times). Same `presets[0]` SOC convention as Task 4.

- [ ] **Step 1: Create `dashboard/src/components/sections/PresetTimeseriesCompare.jsx`**

```jsx
import { useState } from 'react';
import scenarios from '../../data/scenarios.json';
import timeseries from '../../data/timeseries.json';
import { crossProductBarSeries, timeSeriesForCombos } from '../../utils/dataTransforms.js';
import { filterPresetSeries } from '../../utils/presetFilters.js';
import PresetToggleGroup from '../controls/PresetToggleGroup.jsx';
import MetricChart from './MetricChart.jsx';

const DISEASES = [
  { key: 'ng', label: 'Gonorrhoea' },
  { key: 'ct', label: 'Chlamydia' },
  { key: 'tv', label: 'Trichomoniasis' },
  { key: 'syph', label: 'Syphilis' },
];

const METRICS = [
  { key: 'prevalence', barLabel: 'End-of-horizon prevalence', tsLabel: 'Prevalence' },
  { key: 'new_inf', barLabel: 'New infections (cumulative)', tsLabel: 'New infections' },
];

function combosFromPresets(presets) {
  return presets
    .filter((p) => p.key !== 'soc')
    .map((p) => ({ care_level: p.care_level, pn_level: p.pn_level, bp_level: p.bp_level, label: p.label }));
}

export default function PresetTimeseriesCompare({ presets }) {
  const [selected, setSelected] = useState(presets.map((p) => p.key));
  const combos = combosFromPresets(presets);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8">
      <PresetToggleGroup presets={presets} selected={selected} onChange={setSelected} />
      {METRICS.map(({ key: metric, barLabel, tsLabel }) => (
        <div key={metric} className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 last:mb-0">
          {DISEASES.map(({ key, label }) => {
            const barSeries = filterPresetSeries(
              crossProductBarSeries(scenarios, { combos, disease: key, metric }), presets, selected
            );
            const tsSeries = filterPresetSeries(
              timeSeriesForCombos(timeseries, { combos, disease: key, metric }), presets, selected
            );
            return (
              <div key={key}>
                <h3 className="font-semibold text-brand-blue mb-3">{label}</h3>
                <MetricChart data={barSeries} mode="single" yLabel={barLabel} />
                <div className="mt-4">
                  <MetricChart data={tsSeries} mode="timeseries" yLabel={tsLabel} />
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Manually verify the data path with a throwaway script**

```bash
cd dashboard
cat > /tmp/verify-task5.mjs << 'EOF'
import scenarios from './src/data/scenarios.json' with { type: 'json' };
import timeseries from './src/data/timeseries.json' with { type: 'json' };
import { crossProductBarSeries, timeSeriesForCombos } from './src/utils/dataTransforms.js';
import { filterPresetSeries } from './src/utils/presetFilters.js';

const presets = [
  { key: 'soc', label: 'SOC' },
  { key: 'pn_low', label: 'POC + PN low', care_level: 'baseline', pn_level: 'low', bp_level: 'none' },
  { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' },
];
const combos = presets.slice(1).map((p) => ({
  care_level: p.care_level, pn_level: p.pn_level, bp_level: p.bp_level, label: p.label,
}));

for (const metric of ['prevalence', 'new_inf']) {
  for (const disease of ['ng', 'syph']) {
    const bar = filterPresetSeries(
      crossProductBarSeries(scenarios, { combos, disease, metric }), presets, ['soc', 'pn_low', 'pn_high']
    );
    const ts = filterPresetSeries(
      timeSeriesForCombos(timeseries, { combos, disease, metric }), presets, ['soc', 'pn_high']
    );
    console.log(metric, disease, 'bar labels:', bar.map((r) => r.label));
    console.log(metric, disease, 'ts (2 selected) labels:', ts.map((r) => r.label), 'points per series:', ts.map((r) => r.points.length));
  }
}
EOF
node /tmp/verify-task5.mjs
rm /tmp/verify-task5.mjs
```

Expected: `bar labels` always lists all 3 (`SOC`, `POC + PN low`, `POC + PN high`); `ts (2 selected) labels` lists only 2 (`SOC`, `POC + PN high`); `points per series` is `[14, 14]` for both `prevalence` and `new_inf` (2027–2040).

Report the exact output in your report file.

- [ ] **Step 3: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/PresetTimeseriesCompare.jsx
git commit -m "dashboard: add PresetTimeseriesCompare (toggleable multi-preset bar+timeseries)"
```

---

## Task 6: Section 2 — `ResultsHowPocHelps.jsx`

**Files:**
- Create: `dashboard/src/components/sections/ResultsHowPocHelps.jsx`

**Interfaces:**
- Consumes: `OvertreatmentNotificationCompare` (Task 4), `PresetTimeseriesCompare` (Task 5).
- Produces: `ResultsHowPocHelps()` — section component with `id="results-poc"`, wired into `App.jsx` in Task 10.

- [ ] **Step 1: Create `dashboard/src/components/sections/ResultsHowPocHelps.jsx`**

```jsx
import OvertreatmentNotificationCompare from './OvertreatmentNotificationCompare.jsx';
import PresetTimeseriesCompare from './PresetTimeseriesCompare.jsx';

const POC_ALONE_PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
];

export default function ResultsHowPocHelps() {
  return (
    <section id="results-poc" className="py-16 bg-brand-grayLight">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-6">How do POC diagnostics help?</h2>

        <p className="text-brand-gray mb-4 max-w-2xl">
          POC diagnostics will improve correct treatment rates, but cannot eliminate
          overtreatment or over-notification.
        </p>
        <OvertreatmentNotificationCompare presets={POC_ALONE_PRESETS} />

        <p className="text-brand-gray mb-4 max-w-2xl">
          Adding POC diagnostics to syndromic management algorithms will not reduce
          prevalence or incidence.
        </p>
        <PresetTimeseriesCompare presets={POC_ALONE_PRESETS} />
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/ResultsHowPocHelps.jsx
git commit -m "dashboard: add Section 2 (ResultsHowPocHelps)"
```

---

## Task 7: Section 3 — `Hypothesis.jsx`

**Files:**
- Create: `dashboard/src/components/sections/Hypothesis.jsx`

**Interfaces:**
- Consumes: nothing (static content, values hardcoded from `scenarios.py`'s committed constants).
- Produces: `Hypothesis()` — section component with `id="hypothesis"`, wired into `App.jsx` in Task 10.

- [ ] **Step 1: Create `dashboard/src/components/sections/Hypothesis.jsx`**

```jsx
export default function Hypothesis() {
  return (
    <section id="hypothesis" className="py-16">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-4">What else can help?</h2>
        <p className="text-brand-gray mb-6">
          There are also probably pathways from POC diagnostics to improved demand
          generation, partner notification, and bundled prevention. The scenarios below
          explore the roles of demand generation (care-seeking), partner notification, and
          bundled prevention alongside POC diagnostics, each on a baseline/low/moderate/high
          intensity ladder.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border border-gray-200">
            <thead className="bg-brand-grayLight">
              <tr>
                <th className="p-2 text-left">Level</th>
                <th className="p-2 text-right">Care-seeking (× mult.)</th>
                <th className="p-2 text-right">PN — stable: notify / attend f,m</th>
                <th className="p-2 text-right">PN — casual: notify / attend f,m</th>
                <th className="p-2 text-right">Bundled prevention: coverage</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-gray-100">
                <td className="p-2">baseline / none</td>
                <td className="p-2 text-right">1.0×</td>
                <td className="p-2 text-right">20% / 80%, 50%</td>
                <td className="p-2 text-right">10% / 50%, 25%</td>
                <td className="p-2 text-right">0%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">low</td>
                <td className="p-2 text-right">1.25×</td>
                <td className="p-2 text-right">35% / 85%, 60%</td>
                <td className="p-2 text-right">25% / 60%, 40%</td>
                <td className="p-2 text-right">25%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">moderate</td>
                <td className="p-2 text-right">1.5×</td>
                <td className="p-2 text-right">55% / 90%, 70%</td>
                <td className="p-2 text-right">45% / 70%, 55%</td>
                <td className="p-2 text-right">50%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">high</td>
                <td className="p-2 text-right">1.8×</td>
                <td className="p-2 text-right">75% / 92%, 80%</td>
                <td className="p-2 text-right">65% / 80%, 70%</td>
                <td className="p-2 text-right">75%</td>
              </tr>
            </tbody>
          </table>
          <p className="text-xs text-brand-gray mt-2">
            Bundled prevention: 50% relative-susceptibility reduction for 6 months while
            enrolled, fixed across levels — coverage of diagnosed/treated agents enrolled is
            the only varying parameter.
          </p>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/Hypothesis.jsx
git commit -m "dashboard: add Section 3 (Hypothesis) with ladder summary table"
```

---

## Task 8: Section 4 — `ResultsCombinedStrategies.jsx`

**Files:**
- Create: `dashboard/src/components/sections/ResultsCombinedStrategies.jsx`

**Interfaces:**
- Consumes: `PresetTimeseriesCompare` (Task 5), called 3 times with 3 different preset lists.
- Produces: `ResultsCombinedStrategies()` — section component with `id="results-combined"`, wired into `App.jsx` in Task 10.

- [ ] **Step 1: Create `dashboard/src/components/sections/ResultsCombinedStrategies.jsx`**

```jsx
import PresetTimeseriesCompare from './PresetTimeseriesCompare.jsx';

const PN_PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
  { key: 'pn_low', label: 'POC + PN low', care_level: 'baseline', pn_level: 'low', bp_level: 'none' },
  { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
  { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' },
];

const BP_PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
  { key: 'bp_low', label: '+ BP low', care_level: 'baseline', pn_level: 'moderate', bp_level: 'low' },
  { key: 'bp_mod', label: '+ BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
  { key: 'bp_high', label: '+ BP high', care_level: 'baseline', pn_level: 'moderate', bp_level: 'high' },
];

const CS_PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'cs_base', label: 'POC + PN mod + BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
  { key: 'cs_low', label: '+ CS low', care_level: 'low', pn_level: 'moderate', bp_level: 'moderate' },
  { key: 'cs_mod', label: '+ CS mod', care_level: 'moderate', pn_level: 'moderate', bp_level: 'moderate' },
  { key: 'cs_high', label: '+ CS high', care_level: 'high', pn_level: 'moderate', bp_level: 'moderate' },
];

export default function ResultsCombinedStrategies() {
  return (
    <section id="results-combined" className="py-16 bg-brand-grayLight">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-6">Combined strategies</h2>

        <p className="text-brand-gray mb-4 max-w-2xl">
          POC diagnostics + partner notification can decrease prevalence, but incidence
          remains high due to reinfection.
        </p>
        <PresetTimeseriesCompare presets={PN_PRESETS} />

        <p className="text-brand-gray mb-4 max-w-2xl">
          POC diagnostics + bundled prevention can decrease prevalence and incidence.
        </p>
        <PresetTimeseriesCompare presets={BP_PRESETS} />

        <p className="text-brand-gray mb-4 max-w-2xl">
          POC diagnostics + bundled prevention + care-seeking could effectively quash
          syphilis, trichomoniasis, and chlamydia.
        </p>
        <PresetTimeseriesCompare presets={CS_PRESETS} />
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/sections/ResultsCombinedStrategies.jsx
git commit -m "dashboard: add Section 4 (ResultsCombinedStrategies)"
```

---

## Task 9: `Methods.jsx` calibration fix

**Files:**
- Modify: `dashboard/src/components/sections/Methods.jsx`
- Create (copy): `dashboard/src/assets/figures/calib_fig5_sti_timeseries.png`
- Create (copy): `dashboard/src/assets/figures/calib_fig1_syph_timeseries.png`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Methods()` unchanged in signature/usage; only its internal content changes. No other task depends on this one.

- [ ] **Step 1: Copy the two calibration figures into the dashboard's asset directory**

```bash
mkdir -p dashboard/src/assets/figures
cp calibration/artifacts/figures/fig5_sti_timeseries.png dashboard/src/assets/figures/calib_fig5_sti_timeseries.png
cp calibration/artifacts/figures/fig1_syph_timeseries.png dashboard/src/assets/figures/calib_fig1_syph_timeseries.png
```

- [ ] **Step 2: Replace the entire contents of `dashboard/src/components/sections/Methods.jsx`**

```jsx
import { useState } from 'react';
import calibFig5 from '../../assets/figures/calib_fig5_sti_timeseries.png';
import calibFig1 from '../../assets/figures/calib_fig1_syph_timeseries.png';

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
    body: `2000-draw Latin hypercube sample over 19 open parameters (disease betas,
      HIV–syphilis coupling, network structure, syphilis natural history), single-seed
      filtered on sustainability and target pass count, then re-run at 3 seeds per surviving
      draw for robustness. The resulting 169-draw posterior ensemble (507 sims total) is used
      throughout this dashboard — results always reflect that ensemble's spread, not a single
      point estimate.`,
    figures: [
      { src: calibFig5, alt: 'NG/CT/TV prevalence calibration fit against surveillance data' },
      { src: calibFig1, alt: 'Syphilis prevalence calibration fit with ZIMPHIA validation points' },
    ],
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

function AccordionItem({ title, body, figures, open, onToggle }) {
  return (
    <div className="border-b border-gray-200">
      <button onClick={onToggle} className="w-full text-left py-3 flex justify-between items-center">
        <span className="font-medium text-brand-blue">{title}</span>
        <span className="text-brand-gray">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="pb-4">
          <p className="text-sm text-brand-gray">{body}</p>
          {figures && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {figures.map((fig) => (
                <img key={fig.src} src={fig.src} alt={fig.alt} className="w-full border border-gray-200 rounded-lg" />
              ))}
            </div>
          )}
        </div>
      )}
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
            figures={item.figures}
            open={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Verify the build still succeeds**

Run: `cd dashboard && npm run build`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/sections/Methods.jsx dashboard/src/assets/figures/calib_fig5_sti_timeseries.png dashboard/src/assets/figures/calib_fig1_syph_timeseries.png
git commit -m "dashboard: fix Methods calibration text (169-draw ensemble) and embed fit figures"
```

---

## Task 10: Wire `App.jsx` and `Header.jsx`, delete `Overview.jsx`/`KeyFindings.jsx`, final verification

**Files:**
- Modify: `dashboard/src/App.jsx`
- Modify: `dashboard/src/components/layout/Header.jsx`
- Delete: `dashboard/src/components/sections/Overview.jsx`
- Delete: `dashboard/src/components/sections/KeyFindings.jsx`

**Interfaces:**
- Consumes: `TheProblem` (Task 3), `ResultsHowPocHelps` (Task 6), `Hypothesis` (Task 7), `ResultsCombinedStrategies` (Task 8), `ScenarioExplorer`/`Methods` (unchanged).
- Produces: the fully assembled app. This is the integration checkpoint — first point the new section order, nav, and deletions are all live together.

- [ ] **Step 1: Replace the entire contents of `dashboard/src/App.jsx`**

```jsx
import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import TheProblem from './components/sections/TheProblem.jsx';
import ResultsHowPocHelps from './components/sections/ResultsHowPocHelps.jsx';
import Hypothesis from './components/sections/Hypothesis.jsx';
import ResultsCombinedStrategies from './components/sections/ResultsCombinedStrategies.jsx';
import ScenarioExplorer from './components/sections/ScenarioExplorer.jsx';
import Methods from './components/sections/Methods.jsx';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <Header />
      <main className="flex-1">
        <TheProblem />
        <ResultsHowPocHelps />
        <Hypothesis />
        <ResultsCombinedStrategies />
        <ScenarioExplorer />
        <Methods />
      </main>
      <Footer />
    </div>
  );
}
```

- [ ] **Step 2: Replace the entire contents of `dashboard/src/components/layout/Header.jsx`**

The existing nav links to `#overview` and `#findings`, which no longer exist after this plan's section renames. Update to the new section IDs:

```jsx
export default function Header() {
  return (
    <header className="sticky top-0 bg-white border-b border-gray-200 z-10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <span className="font-semibold text-brand-blue">STI Notification — Scenario Dashboard</span>
        <nav className="flex gap-4 text-sm text-brand-gray">
          <a href="#problem" className="hover:text-brand-teal">Problem</a>
          <a href="#results-poc" className="hover:text-brand-teal">How POC helps</a>
          <a href="#hypothesis" className="hover:text-brand-teal">Hypothesis</a>
          <a href="#results-combined" className="hover:text-brand-teal">Combined</a>
          <a href="#explorer" className="hover:text-brand-teal">Explorer</a>
          <a href="#methods" className="hover:text-brand-teal">Methods</a>
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Delete the two superseded section files**

```bash
git rm dashboard/src/components/sections/Overview.jsx dashboard/src/components/sections/KeyFindings.jsx
```

- [ ] **Step 4: Run the test suite**

Run: `cd dashboard && npx vitest run`
Expected: PASS (all tests from Task 1 plus the pre-existing `dataTransforms.test.js` tests — this task doesn't touch either test file).

- [ ] **Step 5: Run the production build**

Run: `cd dashboard && npm run build`
Expected: succeeds, no errors, no unresolved-import warnings — confirms the `Overview.jsx`/`KeyFindings.jsx` deletion left no dangling imports anywhere (in particular, nothing outside `App.jsx` ever imported them, per the grep already done during planning).

- [ ] **Step 6: Manual verification**

Since there's no headless browser in this environment, verify at the data level once more, end-to-end, using the real preset arrays from Tasks 6 and 8:

```bash
cd dashboard
cat > /tmp/verify-task10.mjs << 'EOF'
import scenarios from './src/data/scenarios.json' with { type: 'json' };
import timeseries from './src/data/timeseries.json' with { type: 'json' };
import { crossProductBarSeries, timeSeriesForCombos, crossProductNotificationSeries } from './src/utils/dataTransforms.js';
import { filterPresetSeries } from './src/utils/presetFilters.js';

const presetSets = {
  poc_alone: [
    { key: 'soc', label: 'SOC' },
    { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
  ],
  pn: [
    { key: 'soc', label: 'SOC' },
    { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
    { key: 'pn_low', label: 'POC + PN low', care_level: 'baseline', pn_level: 'low', bp_level: 'none' },
    { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
    { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' },
  ],
  bp: [
    { key: 'soc', label: 'SOC' },
    { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
    { key: 'bp_low', label: '+ BP low', care_level: 'baseline', pn_level: 'moderate', bp_level: 'low' },
    { key: 'bp_mod', label: '+ BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'bp_high', label: '+ BP high', care_level: 'baseline', pn_level: 'moderate', bp_level: 'high' },
  ],
  cs: [
    { key: 'soc', label: 'SOC' },
    { key: 'cs_base', label: 'POC + PN mod + BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_low', label: '+ CS low', care_level: 'low', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_mod', label: '+ CS mod', care_level: 'moderate', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_high', label: '+ CS high', care_level: 'high', pn_level: 'moderate', bp_level: 'moderate' },
  ],
};

for (const [name, presets] of Object.entries(presetSets)) {
  const combos = presets.slice(1).map((p) => ({
    care_level: p.care_level, pn_level: p.pn_level, bp_level: p.bp_level, label: p.label,
  }));
  const allKeys = presets.map((p) => p.key);
  for (const disease of ['ng', 'ct', 'tv', 'syph']) {
    const bar = filterPresetSeries(crossProductBarSeries(scenarios, { combos, disease, metric: 'prevalence' }), presets, allKeys);
    const ts = filterPresetSeries(timeSeriesForCombos(timeseries, { combos, disease, metric: 'prevalence' }), presets, allKeys);
    if (bar.length !== presets.length) throw new Error(`${name}/${disease}: expected ${presets.length} bar entries, got ${bar.length}`);
    if (ts.some((r) => r.points.length !== 14)) throw new Error(`${name}/${disease}: expected 14 points per series`);
    if (bar.some((r) => r.median == null)) throw new Error(`${name}/${disease}: null median in bar data`);
  }
  const overtreat = filterPresetSeries(crossProductBarSeries(scenarios, { combos, disease: 'ng', metric: 'overtreatment' }), presets, allKeys);
  const notif = filterPresetSeries(crossProductNotificationSeries(scenarios, { combos }), presets, allKeys);
  console.log(name, 'OK —', bar.length, 'presets,', overtreat.length, 'overtreatment entries,', notif.length, 'notification entries');
}
console.log('All preset sets verified.');
EOF
node /tmp/verify-task10.mjs
rm /tmp/verify-task10.mjs
```

Expected: `console.log` line for each of the 4 preset sets ending "All preset sets verified." with no thrown errors. Report the exact output.

- [ ] **Step 7: Commit**

```bash
git add dashboard/src/App.jsx dashboard/src/components/layout/Header.jsx
git commit -m "dashboard: wire new narrative sections into App, update nav, remove Overview/KeyFindings"
```

---

## Self-review notes

- **Spec coverage:** all 4 narrative sections (Tasks 3, 6, 7, 8), both new shared components (Tasks 1, 2, 4, 5), the Methods fix (Task 9), and final integration including the `Header.jsx` nav gap found during planning (Task 10) are each covered by a task. `fig_slide5/6/9/10/11.png` are explicitly not embedded per the spec's "Out of scope" section — confirmed no task embeds them.
- **Type/name consistency:** `filterPresetSeries(series, presets, selectedKeys)` (Task 1) is called identically in Tasks 4, 5, and 10's verification script. `combosFromPresets` is duplicated verbatim in Tasks 4 and 5 (two different files) rather than extracted to a shared module — acceptable per YAGNI, since the spec explicitly scopes `dataTransforms.js` as unchanged and this is a 4-line function with no other natural home; extracting a third shared util for a 4-line function used twice would be premature.
- **Placeholder scan:** no TBD/TODO; every step has literal code or an exact command with expected output.
</content>
