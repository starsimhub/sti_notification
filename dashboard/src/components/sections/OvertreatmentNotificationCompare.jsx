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
