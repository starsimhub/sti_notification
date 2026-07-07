# sti_notification scenario dashboard — design

## Purpose

Public, interactive companion to the sti_notification manuscript (health impact
of POC diagnostics, partner notification, bundled prevention, and demand
generation on STI undertreatment in Zimbabwe). Lets a reader explore the full
scenario factorial themselves, beyond the curated combinations shown in the
manuscript figures and the `20260622 PN kickoff.pptx` deck.

Audience: manuscript readers/reviewers. Not an internal analysis tool — the
Python side (`plotting/`, `diagnostics/`) remains the place for exploratory
analysis.

## Location & stack

`sti_notification/dashboard/` — a subfolder inside this repo (like
`klebsim-dashboard/` inside `klebsim`), not a separate repo. React + Vite +
Tailwind CSS + Recharts, matching the established local convention from
`vmb-dashboard` and `klebsim-dashboard`. Ships as a static build; deployment
(Vercel/GitHub Pages) is a later decision once the manuscript is closer to
submission — out of scope for this spec.

```
dashboard/
├── scripts/
│   └── export_data.py       # results/*.csv + scenarios.py ladders -> public/data/*.json
├── public/data/
│   ├── scenarios.json       # from scenarios.kavg.csv
│   ├── ppv_table.json       # from ppv_table.csv
│   ├── diagnostic_performance.json  # from slide4_diagnostic_performance.csv
│   └── ladders.json         # PN_INTENSITY / CARE_SEEKING / BUNDLED_PREVENTION labels+levels, from scenarios.py
├── src/
│   ├── components/
│   │   ├── layout/    Header.jsx, Footer.jsx
│   │   ├── controls/  DiseaseSelect, ArmToggle, CareSeekSelect, PNIntensitySelect, BundledPrevSelect
│   │   ├── charts/    PrevalenceChart, NewInfectionsChart, OvertreatmentChart, NotificationChart
│   │   └── sections/  Overview.jsx, ScenarioExplorer.jsx, KeyFindings.jsx, Methods.jsx
│   ├── utils/dataTransforms.js
│   └── App.jsx
├── package.json / vite.config.js / tailwind.config.js
```

## Data pipeline

`scripts/export_data.py` is the single Python entry point that regenerates
everything under `public/data/`. It:

1. Imports `PN_INTENSITY`, `CARE_SEEKING`, `BUNDLED_PREVENTION` directly from
   `scenarios.py` for ladder level labels — never hardcoded in JS, so the
   dashboard can't drift from the model's actual scenario definitions.
2. Reads `results/scenarios.kavg.csv`, reshapes wide-per-disease columns into
   one JSON record per (cell, draw) with a nested `diseases: {hiv, ng, ct, tv,
   syph}` object, each holding `prev_end`, `new_inf`, `new_treated`,
   `new_treated_unnecessary`, `prop_treated`. Also carries the top-level PN
   over/under-notification fields (`pn_new_notified`, `pn_new_notified_no_sti`,
   `pn_new_attending`, `pn_new_attended_no_sti`, `pn_new_index_total`,
   `pn_new_index_no_sti`).
3. Reads `results/ppv_table.csv` and `results/slide4_diagnostic_performance.csv`
   for the Overview section's SOC-vs-POC sensitivity/specificity/PPV table and
   diagnostic decision-tree numbers.
4. Writes pretty-printed JSON (not minified) so the exported data is
   diffable/reviewable in PRs like any other committed artifact.

Run manually (`conda run -n starsim python dashboard/scripts/export_data.py`)
whenever the calibration/scenario results are refreshed — not wired into any
CI/automated pipeline for now.

**Metric definitions to pin down during implementation** (not architectural,
but need one concrete choice each, checked against `diagnostics/
specificity_tracer.py`'s definitions for consistency):
- Undertreatment: proportion of true infections not successfully treated.
- Under-notification: true-infected indices who did not trigger notification.

## Components

### Overview
Motivation narrative from the kickoff deck (slides 2–5): the cascade drop-off
from infection to cure, why syndromic management is imprecise, the POC
diagnostic decision-tree (SOC vs POC branching, from
`diagnostic_performance.json`), and the SOC-vs-POC sensitivity/specificity/PPV
table by disease (from `ppv_table.json`).

### ScenarioExplorer (priority component)
The new piece beyond the deck: exposes the **full** 65-cell factorial, not
just the 5 curated lever combinations in the deck's "Result N" slides. Controls:
disease selector (HIV/NG/CT/TV/syph), SOC/POC toggle, and independent
selectors for each of the 3 ladders (care-seeking, PN intensity, bundled
prevention — each disabled/greyed under SOC, since ladders only diverge from
baseline post-2027 under POC per `ANALYSIS_PLAN.md`). Shows median + IQR band
per selected outcome across the ensemble's draws, for prevalence, new
infections, overtreatment, and over-notification — mirroring the
`med_iqr` pattern in `plotting/plot_slide6.py`.

### KeyFindings
The deck's 5 numbered "Results" as narrative cards, but with stats **computed
live** from `scenarios.json` at specific lever combinations (SOC vs POC-alone;
POC+PN; POC+bundled-prevention; POC+demand-generation) rather than hardcoded
from the deck — so these numbers can't go stale relative to the explorer's
live data as the calibration evolves.

### Methods
Collapsible accordion: model description, calibration approach (from
`CLAUDE.md`'s "Calibration approach" section), scenario design (the 3 ladders
+ SOC/POC factorial from `ANALYSIS_PLAN.md`). Thin appendix-style section,
text-only — no new data exports needed beyond what Overview/KeyFindings
already pull in.

## Out of scope for this spec
- Deployment/hosting decision (Vercel vs GitHub Pages) — deferred.
- Cost-effectiveness and RCT-bridge sections (present in `vmb-dashboard` but
  not applicable here — no CEA or RCT in this project).
- Any server-side component — the app is fully static, reading only the
  committed JSON snapshots in `public/data/`.
- Wiring `export_data.py` into CI — manual regeneration only, for now.

## Testing / verification
- `npm run build` must succeed with no console errors.
- Manually verify in the browser: every ladder/disease/arm combination in the
  explorer renders a chart (no silent empty states from a missing cell).
- Spot-check 2–3 KeyFindings numbers against the equivalent values in
  `figures/fig_slide7.png` / `fig_slide8.png` (or their underlying
  `results/*.csv`) to confirm the live computation matches the deck's
  narrative direction, even though the exact numbers may have shifted since
  the deck was made.
