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
