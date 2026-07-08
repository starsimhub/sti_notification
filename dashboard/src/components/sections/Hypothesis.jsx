export default function Hypothesis() {
  return (
    <section id="hypothesis" className="py-16">
      <div className="max-w-4xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-4">What else can help?</h2>
        <p className="text-brand-gray mb-6">
          There are also probably pathways from POC diagnostics to improved demand
          generation, partner notification, and bundled prevention. The scenarios below
          explore the roles of demand generation (care-seeking), partner notification, and
          bundled prevention alongside POC diagnostics, each on a baseline/low/moderate/high
          intensity ladder.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border border-gray-200">
            <thead className="bg-brand-grayLight">
              <tr>
                <th className="p-2 text-left">Level</th>
                <th className="p-2 text-right">Care-seeking (× mult.)</th>
                <th className="p-2 text-right">PN — stable: notify / attend f,m</th>
                <th className="p-2 text-right">PN — casual: notify / attend f,m</th>
                <th className="p-2 text-right">Bundled prevention: coverage</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-gray-100">
                <td className="p-2">baseline / none</td>
                <td className="p-2 text-right">1.0×</td>
                <td className="p-2 text-right">20% / 80%, 50%</td>
                <td className="p-2 text-right">10% / 50%, 25%</td>
                <td className="p-2 text-right">0%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">low</td>
                <td className="p-2 text-right">1.25×</td>
                <td className="p-2 text-right">35% / 85%, 60%</td>
                <td className="p-2 text-right">25% / 60%, 40%</td>
                <td className="p-2 text-right">25%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">moderate</td>
                <td className="p-2 text-right">1.5×</td>
                <td className="p-2 text-right">55% / 90%, 70%</td>
                <td className="p-2 text-right">45% / 70%, 55%</td>
                <td className="p-2 text-right">50%</td>
              </tr>
              <tr className="border-t border-gray-100">
                <td className="p-2">high</td>
                <td className="p-2 text-right">1.8×</td>
                <td className="p-2 text-right">75% / 92%, 80%</td>
                <td className="p-2 text-right">65% / 80%, 70%</td>
                <td className="p-2 text-right">75%</td>
              </tr>
            </tbody>
          </table>
          <p className="text-xs text-brand-gray mt-2">
            Bundled prevention: 50% relative-susceptibility reduction for 6 months while
            enrolled, fixed across levels — coverage of diagnosed/treated agents enrolled is
            the only varying parameter.
          </p>
        </div>
      </div>
    </section>
  );
}
