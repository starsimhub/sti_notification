import { useState } from 'react';

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
    body: `500-draw Latin hypercube sample over 17 open parameters (disease betas, HIV–syphilis
      coupling, network structure, syphilis natural history), K=5 seed-averaged per draw,
      scored by continuous weighted goodness-of-fit against Zimbabwe HIV/STI prevalence data
      and ZIMPHIA age-by-sex syphilis tables. The top-30 draws by fit form the posterior
      ensemble used throughout this dashboard — results always reflect that ensemble's spread,
      not a single point estimate.`,
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

function AccordionItem({ title, body, open, onToggle }) {
  return (
    <div className="border-b border-gray-200">
      <button onClick={onToggle} className="w-full text-left py-3 flex justify-between items-center">
        <span className="font-medium text-brand-blue">{title}</span>
        <span className="text-brand-gray">{open ? '−' : '+'}</span>
      </button>
      {open && <p className="pb-4 text-sm text-brand-gray">{body}</p>}
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
            open={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
          />
        ))}
      </div>
    </section>
  );
}
