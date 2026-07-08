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
