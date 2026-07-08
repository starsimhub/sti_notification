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
