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
          <LadderLevelSelect label="Vary" levels={AXES} labels={AXIS_LABELS} value={varyAxis} onChange={setVaryAxis} />
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
