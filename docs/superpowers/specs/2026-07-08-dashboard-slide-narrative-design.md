# Dashboard slide-narrative redesign

## Purpose

Restructure the sti_notification dashboard's opening narrative (currently
`Overview.jsx` + `KeyFindings.jsx`) to follow the four-section story already
told in the project's slide deck (`figures/fig_slide*.png`): the problem,
how POC diagnostics help, a hypothesis about what else could help, and
results for combined strategies. Embed the relevant static slide figures
where the narrative is illustrative-only, and rebuild the figures that
compare SOC vs POC (and POC + other levers) as interactive charts driven by
the dashboard's real data, so readers can toggle scenarios on and off
instead of seeing a fixed static comparison. The existing full
`ScenarioExplorer` (checkbox cross-product across all three levers, all
four diseases) is unchanged and keeps its place as the dashboard's
"explore everything yourself" endpoint, now positioned after the narrative
sections rather than being the narrative itself.

## Scope change from the current dashboard

**Before:** `Overview.jsx` opens with two paragraphs and the
diagnostic-performance table; `KeyFindings.jsx` follows the
`ScenarioExplorer` with five static text-and-number "Result N" cards
summarizing hand-picked scenario contrasts.

**After:** Four narrative sections mirror the slide deck's structure
exactly, each with its own heading, text, and figures (static image or
interactive chart as appropriate); `ScenarioExplorer` moves after them,
kept byte-for-byte as-is; `Methods` keeps its existing accordion shape but
gets a corrected "Calibration" body and two embedded calibration figures.
`Overview.jsx` and `KeyFindings.jsx` are deleted.

## Global constraints (carried over from the existing dashboard)

- Diseases: `ng`, `ct`, `tv`, `syph` only — HIV excluded everywhere, as
  established in the scenario-explorer-multiselect plan.
- All new interactive charts reuse the **existing, unchanged**
  `dataTransforms.js` functions (`crossProductBarSeries`,
  `crossProductNotificationSeries`, `timeSeriesForCombos`,
  `crossProductCombos`) and the **existing, unchanged** `MetricChart.jsx`
  modes (`'single'`, `'notification'`, `'timeseries'`). No changes to
  either file are in scope for this plan.
- Color convention is unchanged: SOC always `SOC_COLOR` (gray); other
  series cycle `MetricChart`'s existing `PALETTE` by index.
- Static slide images that are purely illustrative (not a SOC-vs-POC or
  multi-scenario comparison the dashboard's data can reproduce) are
  embedded as plain images, not rebuilt as charts.

## File structure

```
dashboard/
├── src/
│   ├── App.jsx                                    # section order changed
│   ├── assets/
│   │   └── figures/                               # NEW — copied from repo-root figures/
│   │       ├── fig_slide2.png
│   │       ├── fig_slide3.png
│   │       ├── fig_slide4.png
│   │       ├── calib_fig1_syph_timeseries.png      # copied from calibration/artifacts/figures/fig1_syph_timeseries.png
│   │       └── calib_fig5_sti_timeseries.png       # copied from calibration/artifacts/figures/fig5_sti_timeseries.png
│   ├── components/
│   │   ├── controls/
│   │   │   └── PresetToggleGroup.jsx               # NEW
│   │   └── sections/
│   │       ├── Overview.jsx                        # DELETE
│   │       ├── KeyFindings.jsx                     # DELETE
│   │       ├── TheProblem.jsx                      # NEW (replaces Overview.jsx)
│   │       ├── ResultsHowPocHelps.jsx               # NEW (replaces KeyFindings.jsx)
│   │       ├── Hypothesis.jsx                       # NEW
│   │       ├── ResultsCombinedStrategies.jsx        # NEW
│   │       ├── OvertreatmentNotificationCompare.jsx # NEW
│   │       ├── PresetTimeseriesCompare.jsx          # NEW
│   │       ├── ScenarioExplorer.jsx                 # unchanged
│   │       ├── MetricChart.jsx                      # unchanged
│   │       └── Methods.jsx                          # content fix only
```

Images are imported via ES `import` (`import fig2 from '../../assets/figures/fig_slide2.png'`,
then `<img src={fig2} />`), matching Vite's existing asset-hashing pipeline
— no `public/` directory is introduced, since the project doesn't use one
today and `base: './'` in `vite.config.js` makes hashed asset imports the
path-safe choice for the GitHub Pages subpath deploy.

## New shared components

### `PresetToggleGroup.jsx` (`controls/`)

```
PresetToggleGroup({ presets: [{key, label}], selected: string[], onChange })
```

Renders one checkbox per preset. Sibling to the existing
`LadderCheckboxGroup` — same "at least one stays checked" guard (clicking
the last checked box is a no-op) — but keyed on arbitrary preset `key`s
rather than ladder axis levels, since these presets are named,
editorially-chosen combinations, not a cross-product axis.

### `PresetTimeseriesCompare.jsx` (`sections/`)

```
PresetTimeseriesCompare({ presets: [{key, label, care_level?, pn_level?, bp_level?}] })
```

- `presets[0]` is always the SOC row — convention: `key === 'soc'`, no
  level fields needed. All other presets carry the three level fields
  needed to build a `combos` entry.
- Builds `combos` from `presets.slice(1)` (each mapped to
  `{care_level, pn_level, bp_level, label}`) and calls the existing
  `crossProductBarSeries`/`timeSeriesForCombos` once per disease — these
  functions already prepend the real SOC (`poc: false`) row automatically,
  so no new SOC-handling logic is needed in `dataTransforms.js`.
- Filters the resulting `{label, isSoc, ...}` arrays down to whichever
  preset keys are currently checked in a `PresetToggleGroup` rendered
  above the charts (all presets checked by default).
- Renders two 2×2 disease grids (NG/CT/TV/syph), one for `prevalence` one
  for `new_inf`, each panel = `MetricChart` `'single'` (bar) stacked above
  `MetricChart` `'timeseries'` (line) — i.e., exactly `ScenarioExplorer`'s
  existing per-disease panel layout, reused verbatim, with both metrics
  always shown (no metric-tab switcher — unlike the full explorer, each
  usage here is making one specific point about one specific metric pair).

Reused 4 times: Section 2 bullet 2, Section 4 bullets 1–3 — see "Section
content" below for each call site's exact `presets` array.

### `OvertreatmentNotificationCompare.jsx` (`sections/`)

```
OvertreatmentNotificationCompare({ presets: [{key, label, care_level?, pn_level?, bp_level?}] })
```

Same toggle/filter pattern as `PresetTimeseriesCompare`, but renders a 2×2
disease grid of `crossProductBarSeries(..., {metric: 'overtreatment'})`
bar-only panels, plus one `crossProductNotificationSeries` bar chart
alongside (no disease dimension, matching `MetricChart`'s existing
`'notification'` mode). Kept as a separate component rather than a mode
flag on `PresetTimeseriesCompare` because the data shape (bar-only, one
extra non-disease chart) and layout genuinely differ.

Used once: Section 2 bullet 1.

## Section content

### Section 1 — `TheProblem.jsx` (`id="problem"`)

1. Existing intro paragraph ("Most curable STIs in women are
   asymptomatic...") — carried over from `Overview.jsx` unchanged.
2. **`fig_slide2.png`** embedded — the 4-disease acquisition→cure cascade
   drop-off bars. Caption reuses the image's own footnote text: "Steps
   from model parameters (symptomatic, care-seeking 0.49, syndromic
   routing, cure). Reinfection: CT measured (50%); provisional elsewhere.
   Grey = lost at each step. Preliminary: draw 66, single seed."
3. Existing second paragraph ("Syndromic management can't distinguish...")
   — carried over unchanged.
4. **Diagnostic performance, SOC vs POC** table — moved as-is from
   `Overview.jsx` (same `diagnostic_performance.json`, same markup).
5. New lead-in sentence — "The poor specificity of syndromic management
   leads to a sizable number of unnecessary treatments and unwarranted
   partner notifications" — followed by **`fig_slide3.png`** embedded.
6. New lead-in sentence — "Despite improvements in sensitivity and
   specificity, low prevalence means we should temper our expectations
   around the reduction in overtreatment" — followed by **`fig_slide4.png`**
   embedded.

All four images render inside a `max-w`-constrained `<img>` with a light
border, consistent with the existing table's container styling. No chart
code involved.

### Section 2 — `ResultsHowPocHelps.jsx` (`id="results-poc"`)

1. Text: "POC diagnostics will improve correct treatment rates, but cannot
   eliminate overtreatment or over-notification." →
   `OvertreatmentNotificationCompare` with:
   ```
   [{ key: 'soc', label: 'SOC' },
    { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' }]
   ```
2. Text: "Adding POC diagnostics to syndromic management algorithms will
   not reduce prevalence or incidence." → `PresetTimeseriesCompare` with
   the same 2 presets as above.

`fig_slide5.png` and `fig_slide6.png` are **not** embedded — fully
superseded by their interactive equivalents. (`fig_slide5.png`'s
VDS-treatment, GUD-treatment, and female→male-notification-cascade panels
have no corresponding data in `scenarios.json` and are out of scope; see
"Out of scope" below.)

### Section 3 — `Hypothesis.jsx` (`id="hypothesis"`)

1. Text: "There are also probably pathways from POC diagnostics to
   improved demand generation, partner notification, and bundled
   prevention" + a short framing sentence introducing the three levers
   explored in Section 4.
2. A static ladder-summary table, values sourced from `scenarios.py`'s
   committed constants (`PN_INTENSITY`, `CARE_SEEKING`,
   `BUNDLED_PREVENTION`) — hardcoded JSX, not a new JSON export, since
   these are fixed ladder definitions that don't vary per scenario run:

   | Level | Care-seeking (× mult.) | PN — stable: notify / attend f,m | PN — casual: notify / attend f,m | Bundled prevention: coverage |
   |---|---|---|---|---|
   | baseline / none | 1.0× | 20% / 80%, 50% | 10% / 50%, 25% | 0% |
   | low | 1.25× | 35% / 85%, 60% | 25% / 60%, 40% | 25% |
   | moderate | 1.5× | 55% / 90%, 70% | 45% / 70%, 55% | 50% |
   | high | 1.8× | 75% / 92%, 80% | 65% / 80%, 70% | 75% |

   Footnote: "Bundled prevention: 50% relative-susceptibility reduction
   for 6 months while enrolled, fixed across levels — coverage of
   diagnosed/treated agents enrolled is the only varying parameter."
   Table wrapped in `overflow-x-auto` (matches the Section 1 diagnostic
   table's pattern), since it's wide.

### Section 4 — `ResultsCombinedStrategies.jsx` (`id="results-combined"`)

Three bullets, each with its own `PresetTimeseriesCompare` call. Preset
labels and level values are read directly off the slide legends
(`fig_slide9/10/11.png`):

1. "POC + partner notification can decrease prevalence, but incidence
   remains high due to reinfection" — care=`baseline`, bp=`none` fixed:
   ```
   [{ key: 'soc', label: 'SOC' },
    { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
    { key: 'pn_low', label: 'POC + PN low', care_level: 'baseline', pn_level: 'low', bp_level: 'none' },
    { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
    { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' }]
   ```
2. "POC + bundled prevention can decrease prevalence and incidence" —
   care=`baseline`, pn=`moderate` fixed:
   ```
   [{ key: 'soc', label: 'SOC' },
    { key: 'pn_mod', label: 'POC + PN mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'none' },
    { key: 'bp_low', label: '+ BP low', care_level: 'baseline', pn_level: 'moderate', bp_level: 'low' },
    { key: 'bp_mod', label: '+ BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'bp_high', label: '+ BP high', care_level: 'baseline', pn_level: 'moderate', bp_level: 'high' }]
   ```
3. "POC + bundled prevention + care-seeking could effectively quash
   syphilis, trichomoniasis, and chlamydia" — pn=`moderate`, bp=`moderate`
   fixed:
   ```
   [{ key: 'soc', label: 'SOC' },
    { key: 'cs_base', label: 'POC + PN mod + BP mod', care_level: 'baseline', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_low', label: '+ CS low', care_level: 'low', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_mod', label: '+ CS mod', care_level: 'moderate', pn_level: 'moderate', bp_level: 'moderate' },
    { key: 'cs_high', label: '+ CS high', care_level: 'high', pn_level: 'moderate', bp_level: 'moderate' }]
   ```

`fig_slide9/10/11.png` are **not** embedded — fully superseded by their
interactive equivalents.

### `ScenarioExplorer.jsx`

Unchanged. Moves to immediately after Section 4, keeping its role as the
dashboard's open-ended "explore every combination yourself" endpoint.

### `Methods.jsx`

The "Calibration" accordion item's body is factually wrong (says
"500-draw Latin hypercube sample... top-30 draws by fit form the posterior
ensemble") — the actual, committed calibration
(`calibration/calibration_summary.md`) is a **2000-draw LHS over 19
open parameters**, single-seed filtered on sustainability + target pass
count, then re-run at 3 seeds for robustness, producing the **169-draw
posterior ensemble** (507 sims) used throughout this dashboard. New body
text:

> "2000-draw Latin hypercube sample over 19 open parameters (disease
> betas, HIV–syphilis coupling, network structure, syphilis natural
> history), single-seed filtered on sustainability and target pass count,
> then re-run at 3 seeds per surviving draw for robustness. The resulting
> 169-draw posterior ensemble (507 sims total) is used throughout this
> dashboard — results always reflect that ensemble's spread, not a single
> point estimate."

Two figures embedded underneath that accordion item's body when open:
`calib_fig5_sti_timeseries.png` (NG/CT/TV prevalence fit) and
`calib_fig1_syph_timeseries.png` (syphilis fit + ZIMPHIA validation
points), side by side on desktop, stacked on mobile.

## Uncertainty treatment

Unchanged from the existing dashboard: bars keep IQR error bars,
time-series lines show medians only (`MetricChart`'s existing modes,
untouched).

## Testing

`PresetToggleGroup`'s toggle/guard logic and the preset-filtering logic in
`PresetTimeseriesCompare`/`OvertreatmentNotificationCompare` (mapping
checked preset keys → the subset of the `crossProductBarSeries`/etc.
output arrays to render) are the only genuinely new logic in this plan —
everything else is JSX composition, static content, or calls into
already-tested functions. Unit tests target that filtering logic
specifically (e.g., "given 3 presets and 2 checked, the chart data has
exactly 2 entries, in the original preset array's order — not the order
the user happened to check them in — with SOC's `isSoc` flag intact").

## Out of scope

- `fig_slide5.png`'s VDS-treatment, GUD-treatment, and
  female→male-notification-cascade panels — no corresponding data in
  `scenarios.json`; would require new Python export work, not requested
  here.
- `fig_slide12.png`/`fig_slide13.png` — not referenced by the user's
  section outline, not embedded.
- No changes to `dataTransforms.js`, `MetricChart.jsx`, or
  `ScenarioExplorer.jsx` — all new interactivity is built by composing
  existing, unchanged functions/components.
- No new Python export step — all data consumed here (`scenarios.json`,
  `timeseries.json`, `diagnostic_performance.json`) already exists from
  prior plans.
</content>
