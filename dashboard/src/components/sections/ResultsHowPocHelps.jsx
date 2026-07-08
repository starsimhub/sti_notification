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
