import { useState } from 'react';
import calibFig5 from '../../assets/figures/calib_fig5_sti_timeseries.png';
import calibFig1 from '../../assets/figures/calib_fig1_syph_timeseries.png';

const ITEMS = [
  {
    title: 'Model',
    body: `STIsim simulation of HIV, syphilis, gonorrhoea (NG), chlamydia (CT), trichomoniasis
      (TV), and bacterial vaginosis (BV) in Zimbabwe, with structured sexual networks and
      partner-notification edges. The custom slot wires a FetalHealth connector for adverse
      pregnancy and birth outcomes.`,
  },
  {
    title: 'Calibration',
    body: `2000-draw Latin hypercube sample over 19 open parameters (disease betas,
      HIV–syphilis coupling, network structure, syphilis natural history), single-seed
      filtered on sustainability and target pass count, then re-run at 3 seeds per surviving
      draw for robustness. The resulting 169-draw posterior ensemble (507 sims total) is used
      throughout this dashboard — results always reflect that ensemble's spread, not a single
      point estimate.`,
    figures: [
      { src: calibFig5, alt: 'NG/CT/TV prevalence calibration fit against surveillance data' },
      { src: calibFig1, alt: 'Syphilis prevalence calibration fit with ZIMPHIA validation points' },
    ],
  },
  {
    title: 'Scenario design',
    body: `Three intensity ladders (care-seeking, partner-notification, bundled prevention),
      each with 4 levels, layered on a standard-of-care (SOC) vs point-of-care (POC)
      diagnostics factorial — 65 cells total (SOC + 4×4×4 POC combinations), each run across
      the full posterior ensemble. Ladders diverge from SOC-equivalent levels only from the
      2027 intervention year onward.`,
  },
];

function AccordionItem({ title, body, figures, open, onToggle }) {
  return (
    <div className="border-b border-gray-200">
      <button onClick={onToggle} className="w-full text-left py-3 flex justify-between items-center">
        <span className="font-medium text-brand-blue">{title}</span>
        <span className="text-brand-gray">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="pb-4">
          <p className="text-sm text-brand-gray">{body}</p>
          {figures && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {figures.map((fig) => (
                <img key={fig.src} src={fig.src} alt={fig.alt} className="w-full border border-gray-200 rounded-lg" />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Methods() {
  const [openIndex, setOpenIndex] = useState(0);
  return (
    <section id="methods" className="py-16 bg-brand-grayLight">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-brand-blue mb-6">Methods</h2>
        {ITEMS.map((item, i) => (
          <AccordionItem
            key={item.title}
            title={item.title}
            body={item.body}
            figures={item.figures}
            open={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  );
}
