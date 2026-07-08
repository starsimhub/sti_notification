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
