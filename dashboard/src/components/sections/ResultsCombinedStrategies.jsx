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
